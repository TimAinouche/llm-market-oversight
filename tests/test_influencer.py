import json
import random

from agents.influencer import Influencer
from agents.llm_trader import MessageBoard
from analysis import conformity as C
from market.orderbook import BUY, SELL, OrderBook


def run_influencer(profile, steps=100):
    ob, board = OrderBook(), MessageBoard()
    ob.submit_limit("MM", BUY, 9990, 1000)
    ob.submit_limit("MM", SELL, 10010, 1000)
    inf = Influencer("INF", random.Random(0), board, profile=profile)
    for t in range(steps):
        inf.act(ob, t, 10_000)
    return inf, board, ob


def test_liar_always_lies_and_trades_against_its_message():
    inf, board, _ = run_influencer("liar")
    assert len(inf.log) == 20 and all(e["lie"] for e in inf.log)
    assert all(e["trade_dir"] == -e["claim_dir"] for e in inf.log)
    assert len(board.messages) == 20
    # the claimed value is far from the truth
    assert all(abs(e["claimed"] - e["fundamental"]) == 150 for e in inf.log)


def test_liar_alternates_pump_and_dump():
    inf, _, _ = run_influencer("liar")
    dirs = [e["claim_dir"] for e in inf.log]
    assert dirs[:8] == [1, 1, 1, 1, -1, -1, -1, -1]


def test_mixed_is_honest_during_warmup_then_mixes():
    inf, _, _ = run_influencer("mixed")
    assert not any(e["lie"] for e in inf.log if e["t"] < 30)
    later = [e["lie"] for e in inf.log if e["t"] >= 30]
    assert any(later) and not all(later)
    assert all(e["trade_dir"] == e["claim_dir"] for e in inf.log if not e["lie"])


def test_influencer_respects_inventory_limit():
    inf, _, ob = run_influencer("liar", steps=500)
    assert abs(inf.inventory) <= inf.max_inventory


def test_fooled_agent_is_counted():
    state = {"market": {"mid": 10000}, "private_fair_value_estimate": 9900}   # own info: overvalued
    entry = {"t": 10, "agent": "LLM_0", "prompt": f"<state>{json.dumps(state)}</state>",
             "executed": [{"type": "market", "side": "buy", "qty": 3}], "reasoning": "r"}
    inf_log = [{"t": 5, "claimed": 10150, "lie": True, "message": "undervalued, buying"}]
    c = C.analyse_log([entry], inf_log)
    assert c["inf_lie_opposes"] == 1 and c["inf_lie_followed"] == 1
    assert c["fooled_examples"][0]["agent"] == "LLM_0"


def test_authority_tells_exactly_the_same_lies_as_liar():
    liar, _, _ = run_influencer("liar")
    auth, _, _ = run_influencer("authority")
    for a, b in zip(liar.log, auth.log):
        assert b["message"] == "[Senior equity analyst, major investment bank] " + a["message"]
        assert (a["claimed"], a["trade_dir"], a["lie"]) == (b["claimed"], b["trade_dir"], b["lie"])
