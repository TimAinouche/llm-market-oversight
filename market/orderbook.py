"""
Limit order book with price-time priority matching.

Conventions:
- Prices are integers in "ticks" (e.g. 10050 = EUR 100.50) to avoid
  floating-point rounding errors.
- A trade always executes at the price of the order that was already resting
  in the book (the "passive" order), as on a real exchange.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from itertools import count
from typing import Optional

BUY = "buy"
SELL = "sell"


@dataclass
class Order:
    order_id: int
    agent_id: str
    side: str              # "buy" or "sell"
    price: Optional[int]   # None for a market order
    qty: int               # remaining quantity
    timestamp: int
    active: bool = True


@dataclass
class Trade:
    buy_order_id: int
    sell_order_id: int
    buyer: str
    seller: str
    price: int
    qty: int
    timestamp: int


@dataclass
class OrderBook:
    # price -> queue of orders at that price (arrival order = time priority)
    bids: dict[int, deque] = field(default_factory=dict)
    asks: dict[int, deque] = field(default_factory=dict)
    orders: dict[int, Order] = field(default_factory=dict)  # index of resting orders, for cancels
    trades: list[Trade] = field(default_factory=list)
    # Full audit trail (orders, cancels, trades), read by the manipulation detectors
    events: list[dict] = field(default_factory=list)
    current_step: int = 0   # set by the simulation loop, used to timestamp events
    _ids: count = field(default_factory=lambda: count(1))
    _clock: count = field(default_factory=lambda: count(0))

    # ------------------------------------------------------------------ #
    # Reading the book
    # ------------------------------------------------------------------ #
    def best_bid(self) -> Optional[int]:
        return max(self.bids) if self.bids else None

    def best_ask(self) -> Optional[int]:
        return min(self.asks) if self.asks else None

    def spread(self) -> Optional[int]:
        bb, ba = self.best_bid(), self.best_ask()
        return None if bb is None or ba is None else ba - bb

    def mid(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        return None if bb is None or ba is None else (bb + ba) / 2

    def depth(self, levels: int = 5) -> dict:
        """Quantity available on the `levels` best price levels of each side."""
        def side_depth(book: dict, reverse: bool):
            prices = sorted(book, reverse=reverse)[:levels]
            return [(p, sum(o.qty for o in book[p])) for p in prices]
        return {"bids": side_depth(self.bids, True), "asks": side_depth(self.asks, False)}

    def snapshot(self, levels: int = 5) -> dict:
        """Market state as a dict (sent to the LLM agents as JSON)."""
        return {
            "best_bid": self.best_bid(),
            "best_ask": self.best_ask(),
            "spread": self.spread(),
            "mid": self.mid(),
            "depth": self.depth(levels),
            "last_trades": [
                {"price": t.price, "qty": t.qty} for t in self.trades[-5:]
            ],
        }

    def open_orders_of(self, agent_id: str) -> list[Order]:
        """Orders of one agent still resting in the book."""
        return [o for o in self.orders.values() if o.agent_id == agent_id and o.active]

    # ------------------------------------------------------------------ #
    # Order entry
    # ------------------------------------------------------------------ #
    def submit_limit(self, agent_id: str, side: str, price: int, qty: int):
        """Limit order: executes against the book where possible, the remainder
        rests in the book. Returns (order_id, list of trades)."""
        self._check(side, qty)
        order = Order(next(self._ids), agent_id, side, price, qty, next(self._clock))
        self._record("order", order_id=order.order_id, agent=agent_id, kind="limit",
                     side=side, price=price, qty=qty)
        trades = self._match(order)
        if order.qty > 0:
            book = self.bids if side == BUY else self.asks
            book.setdefault(price, deque()).append(order)
            self.orders[order.order_id] = order
        else:
            order.active = False
        return order.order_id, trades

    def submit_market(self, agent_id: str, side: str, qty: int):
        """Market order: executes at the best available prices.
        Any unfilled remainder (empty book) is dropped."""
        self._check(side, qty)
        order = Order(next(self._ids), agent_id, side, None, qty, next(self._clock))
        self._record("order", order_id=order.order_id, agent=agent_id, kind="market",
                     side=side, price=None, qty=qty)
        trades = self._match(order)
        order.active = False
        return order.order_id, trades

    def cancel(self, order_id: int) -> bool:
        """Cancels an order still in the book. Returns False if it no longer exists."""
        order = self.orders.pop(order_id, None)
        if order is None or not order.active:
            return False
        order.active = False
        self._record("cancel", order_id=order_id, agent=order.agent_id, side=order.side,
                     price=order.price, remaining_qty=order.qty)
        book = self.bids if order.side == BUY else self.asks
        queue = book[order.price]
        queue.remove(order)
        if not queue:
            del book[order.price]
        return True

    # ------------------------------------------------------------------ #
    # Matching engine
    # ------------------------------------------------------------------ #
    def _match(self, order: Order) -> list[Trade]:
        trades = []
        opposite = self.asks if order.side == BUY else self.bids

        while order.qty > 0 and opposite:
            best = min(opposite) if order.side == BUY else max(opposite)
            # A limit order only executes if its price crosses the best opposite price
            if order.price is not None:
                if order.side == BUY and order.price < best:
                    break
                if order.side == SELL and order.price > best:
                    break

            queue = opposite[best]
            resting = queue[0]                     # time priority: oldest first
            qty = min(order.qty, resting.qty)
            buy, sell = (order, resting) if order.side == BUY else (resting, order)
            trade = Trade(buy.order_id, sell.order_id, buy.agent_id, sell.agent_id,
                          best, qty, next(self._clock))
            trades.append(trade)
            self.trades.append(trade)
            self._record("trade", buy_order_id=buy.order_id, sell_order_id=sell.order_id,
                         buyer=buy.agent_id, seller=sell.agent_id, price=best, qty=qty)

            order.qty -= qty
            resting.qty -= qty
            if resting.qty == 0:
                resting.active = False
                queue.popleft()
                self.orders.pop(resting.order_id, None)
                if not queue:
                    del opposite[best]
        return trades

    def _record(self, event_type: str, **fields) -> None:
        self.events.append({"type": event_type, "step": self.current_step, **fields})

    @staticmethod
    def _check(side: str, qty: int) -> None:
        if side not in (BUY, SELL):
            raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
        if qty <= 0:
            raise ValueError("quantity must be positive")
