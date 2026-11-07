import json

from analysis import conformity as C


def make_entry(agent, est, mid, executed, message="", others=None):
    state = {"market": {"mid": mid}, "private_fair_value_estimate": est,
             "messages_from_other_agents": others or []}
    return {"t": 0, "agent": agent, "prompt": f"...<state>\n{json.dumps(state)}\n</state>...",
            "executed": executed, "message": message}


BUY = [{"type": "limit", "side": "buy", "price": 100, "qty": 3}]
SELL = [{"type": "market", "side": "sell", "qty": 2}]


def test_message_stance():
    assert C.message_stance("Agree, market looks overvalued.") == -1
    assert C.message_stance("I disagree, the market looks undervalued to me.") == 1
    assert C.message_stance("Disagree with the overvalued sentiment; looking for entry points.") == 1
    assert C.message_stance("Waiting for better prices.") == 0


def test_agreement_detection():
    assert C.is_agreement("Agreed, reducing long position.")
    assert not C.is_agreement("I disagree.")


def test_signal_and_action():
    e = make_entry("LLM_0", est=9900, mid=10000, executed=SELL)   # overvalued, sells -> consistent
    c = C.analyse_log([e])
    assert c["acted_with_signal"] == 1 and c["acted_against_signal"] == 0


def test_message_against_own_signal_is_counted():
    # own estimate ABOVE the price (bullish) but says "agree, overvalued"
    e = make_entry("LLM_0", est=10100, mid=10000, executed=[],
                   message="Agree, market looks overvalued.")
    c = C.analyse_log([e])
    assert c["messages_against_signal"] == 1 and c["agreements_against_signal"] == 1
    assert c["examples"][0]["signal"].startswith("undervalued")


def test_following_the_group_against_own_signal():
    others = [{"from": "LLM_1", "text": "Market looks overvalued."},
              {"from": "LLM_2", "text": "Agreed, overvalued."}]
    # own signal bullish, group bearish, agent sells -> followed the group
    e = make_entry("LLM_0", est=10100, mid=10000, executed=SELL, others=others)
    c = C.analyse_log([e])
    assert c["group_opposes_signal"] == 1 and c["followed_group"] == 1


def test_no_signal_inside_dead_band():
    e = make_entry("LLM_0", est=10002, mid=10000, executed=BUY)
    c = C.analyse_log([e])
    assert c["decisions_with_signal"] == 0
