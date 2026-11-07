from market.orderbook import BUY, SELL, OrderBook


def test_non_crossing_limit_orders_rest_in_book():
    ob = OrderBook()
    ob.submit_limit("A", BUY, 99, 10)
    ob.submit_limit("B", SELL, 101, 10)
    assert ob.best_bid() == 99
    assert ob.best_ask() == 101
    assert ob.spread() == 2
    assert ob.trades == []


def test_crossing_order_executes_at_passive_price():
    ob = OrderBook()
    ob.submit_limit("A", SELL, 100, 10)
    _, trades = ob.submit_limit("B", BUY, 102, 10)   # buyer willing to pay more
    assert len(trades) == 1
    assert trades[0].price == 100                    # price of the resting order
    assert trades[0].buyer == "B" and trades[0].seller == "A"
    assert ob.best_ask() is None and ob.best_bid() is None


def test_partial_fill():
    ob = OrderBook()
    ob.submit_limit("A", SELL, 100, 10)
    _, trades = ob.submit_limit("B", BUY, 100, 4)
    assert trades[0].qty == 4
    assert ob.depth()["asks"] == [(100, 6)]          # 6 left on the ask


def test_limit_order_remainder_rests_in_book():
    ob = OrderBook()
    ob.submit_limit("A", SELL, 100, 3)
    ob.submit_limit("B", BUY, 100, 10)
    assert ob.best_bid() == 100
    assert ob.depth()["bids"] == [(100, 7)]


def test_price_then_time_priority():
    ob = OrderBook()
    ob.submit_limit("early", SELL, 100, 5)
    ob.submit_limit("late", SELL, 100, 5)            # same price, arrived later
    ob.submit_limit("expensive", SELL, 101, 5)
    _, trades = ob.submit_market("X", BUY, 12)
    assert [t.seller for t in trades] == ["early", "late", "expensive"]
    assert [t.price for t in trades] == [100, 100, 101]


def test_market_order_on_empty_book_does_nothing():
    ob = OrderBook()
    _, trades = ob.submit_market("X", BUY, 5)
    assert trades == []
    assert ob.best_bid() is None                     # a market order never rests


def test_cancel():
    ob = OrderBook()
    oid, _ = ob.submit_limit("A", BUY, 99, 10)
    assert ob.cancel(oid) is True
    assert ob.best_bid() is None
    assert ob.cancel(oid) is False                   # already cancelled


def test_cannot_cancel_filled_order():
    ob = OrderBook()
    oid, _ = ob.submit_limit("A", SELL, 100, 5)
    ob.submit_market("B", BUY, 5)
    assert ob.cancel(oid) is False


def test_open_orders_of_agent():
    ob = OrderBook()
    ob.submit_limit("A", BUY, 99, 5)
    ob.submit_limit("A", SELL, 105, 5)
    ob.submit_limit("B", BUY, 98, 5)
    assert len(ob.open_orders_of("A")) == 2
    assert len(ob.open_orders_of("B")) == 1


def test_audit_trail_records_orders_cancels_and_trades():
    ob = OrderBook()
    ob.current_step = 3
    oid, _ = ob.submit_limit("A", SELL, 100, 5)
    ob.submit_market("B", BUY, 2)
    ob.current_step = 4
    ob.cancel(oid)
    types = [e["type"] for e in ob.events]
    assert types == ["order", "order", "trade", "cancel"]
    assert ob.events[2]["buyer"] == "B" and ob.events[2]["seller"] == "A"
    assert ob.events[3]["step"] == 4 and ob.events[3]["remaining_qty"] == 3
