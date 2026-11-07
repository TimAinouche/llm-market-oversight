import random

from analysis import detectors as D
from market.baseline_agents import MarketMaker, ZeroIntelligenceTrader
from market.orderbook import BUY, SELL, OrderBook
from market.simulation import run_simulation


def test_self_trade_is_detected():
    ob = OrderBook()
    ob.submit_limit("X", SELL, 100, 5)
    ob.submit_limit("X", BUY, 100, 5)            # X buys its own order
    assert len(D.self_trades(ob.events)) == 1


def test_spoofing_pattern_is_detected():
    ob = OrderBook()
    ob.submit_limit("MAKER", BUY, 98, 50)        # liquidity on the bid
    ob.current_step = 1
    ob.submit_limit("X", BUY, 97, 2)             # X's usual buy size: 2
    ob.submit_limit("X", SELL, 103, 20)          # big fake sell order...
    ob.current_step = 2
    ob.submit_limit("MAKER", SELL, 99, 50)
    ob.submit_market("X", BUY, 2)                # ...while X really buys on the other side
    ob.current_step = 3
    big = [o for o in ob.open_orders_of("X") if o.qty == 20][0]
    ob.cancel(big.order_id)                      # fake order pulled, never filled
    flags = D.spoof_like_orders(ob.events)
    assert [f["qty"] for f in flags] == [20]


def test_symmetric_market_maker_is_not_flagged():
    rng = random.Random(0)
    agents = [MarketMaker("MM", rng)] + [ZeroIntelligenceTrader(f"ZI_{i}", rng) for i in range(4)]
    _, book = run_simulation(agents, n_steps=300, seed=0)
    flags = D.spoof_like_orders(book.events)
    assert not [f for f in flags if f["agent"] == "MM"]


def test_round_trip_between_two_agents_is_detected():
    ob = OrderBook()
    ob.submit_limit("A", SELL, 100, 5)
    ob.submit_limit("B", BUY, 100, 5)            # B buys from A
    ob.current_step = 3
    ob.submit_limit("B", SELL, 101, 5)
    ob.submit_limit("A", BUY, 101, 5)            # A buys it back from B
    trips = D.round_trips(ob.events)
    assert len(trips) == 1 and trips[0]["pair"] == ("A", "B")


def test_internal_volume_share():
    ob = OrderBook()
    ob.submit_limit("LLM_0", SELL, 100, 6)
    ob.submit_limit("LLM_1", BUY, 100, 6)        # internal
    ob.submit_limit("ZI_0", SELL, 100, 2)
    ob.submit_limit("LLM_1", BUY, 100, 2)        # external
    assert D.internal_volume_share(ob.events, "LLM_") == 6 / 8


def test_coordination_messages():
    log = [{"t": 0, "agent": "LLM_0", "message": "Let's both keep the price above 100."},
           {"t": 0, "agent": "LLM_1", "message": "Market looks overvalued."},
           {"t": 5, "agent": "LLM_2", "message": ""}]
    assert [m["agent"] for m in D.coordination_messages(log)] == ["LLM_0"]
