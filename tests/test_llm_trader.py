import json
import random

import pytest

from agents.llm_client import MockClient
from agents.llm_trader import LLMTrader, MessageBoard, extract_json
from market.baseline_agents import MarketMaker, ZeroIntelligenceTrader
from market.orderbook import BUY, SELL, OrderBook
from market.simulation import run_simulation


class ScriptedClient:
    """Returns a fixed answer, to test how the agent handles it."""

    def __init__(self, reply: str):
        self.reply = reply
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.reply


def make_agent(reply, **kw):
    return LLMTrader("LLM_0", random.Random(0), ScriptedClient(reply), act_every=1, **kw)


def test_extract_json_handles_code_fences_and_text():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_valid_actions_are_executed():
    reply = json.dumps({"reasoning": "test", "actions": [
        {"type": "limit", "side": "buy", "price": 9990, "qty": 3},
        {"type": "limit", "side": "sell", "price": 10010, "qty": 2},
    ]})
    agent, book = make_agent(reply), OrderBook()
    agent.act(book, 0, 10_000)
    assert book.best_bid() == 9990 and book.best_ask() == 10010
    assert agent.log[0]["reasoning"] == "test"
    assert len(agent.log[0]["executed"]) == 2


def test_invalid_actions_are_rejected_not_corrected():
    reply = json.dumps({"reasoning": "", "actions": [
        {"type": "limit", "side": "buy", "price": 9990, "qty": 999},   # qty too big
        {"type": "cancel", "order_id": 12345},                         # not its order
        {"type": "teleport"},                                          # unknown
    ]})
    agent, book = make_agent(reply), OrderBook()
    agent.act(book, 0, 10_000)
    assert book.best_bid() is None
    assert len(agent.log[0]["rejected"]) == 3


def test_inventory_limit_counts_pending_orders():
    orders = [{"type": "limit", "side": "buy", "price": 9990, "qty": 10} for _ in range(4)]
    agent = make_agent(json.dumps({"reasoning": "", "actions": orders}), max_inventory=25)
    book = OrderBook()
    agent.act(book, 0, 10_000)
    assert len(agent.log[0]["executed"]) == 2      # 20 shares ok, a 3rd order would exceed 25
    assert len(agent.log[0]["rejected"]) == 2


def test_garbage_answer_is_logged_as_error():
    agent, book = make_agent("I would rather not trade today."), OrderBook()
    agent.act(book, 0, 10_000)
    assert "error" in agent.log[0]


def test_agent_only_decides_every_n_steps():
    agent = LLMTrader("LLM_0", random.Random(0), ScriptedClient('{"actions": []}'), act_every=5)
    book = OrderBook()
    for t in range(10):
        agent.act(book, t, 10_000)
    assert len(agent.log) == 2                     # t = 0 and t = 5


def test_communication_only_when_board_given():
    reply = json.dumps({"reasoning": "", "actions": [], "message_to_other_agents": "hello"})
    board = MessageBoard()
    talker = make_agent(reply, board=board)
    talker.act(OrderBook(), 0, 10_000)
    assert board.messages[0]["text"] == "hello"
    assert "message_to_other_agents" in talker.client.prompts[0]

    silent = make_agent(reply)                      # no board
    silent.act(OrderBook(), 0, 10_000)
    assert "message_to_other_agents" not in silent.client.prompts[0]


def test_prompt_never_mentions_manipulation():
    # The design claim: any manipulation must be emergent, not suggested
    agent = make_agent('{"actions": []}', board=MessageBoard())
    agent.act(OrderBook(), 0, 10_000)
    prompt = agent.client.prompts[0].lower()
    for word in ("manipulat", "collu", "spoof", "coordinat", "cooperat", "illegal"):
        assert word not in prompt


def test_full_simulation_with_mock_llm_keeps_accounts_consistent():
    rng = random.Random(1)
    client = MockClient(seed=1)
    agents = [MarketMaker("MM", rng)] + [ZeroIntelligenceTrader(f"ZI_{i}", rng) for i in range(2)]
    agents += [LLMTrader(f"LLM_{i}", rng, client, act_every=5) for i in range(2)]
    run_simulation(agents, n_steps=60, seed=1)
    assert sum(a.inventory for a in agents) == 0
    assert sum(a.cash for a in agents) == 0
    assert client.n_calls == 2 * 12
    for a in agents[-2:]:
        assert abs(a.inventory) <= a.max_inventory
