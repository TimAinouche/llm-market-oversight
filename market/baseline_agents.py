"""
Baseline (non-LLM) agents.

They are the control group: if a behaviour appears with LLM agents but not
with these simple agents, it can be attributed to the LLMs.

- ZeroIntelligenceTrader: inspired by Gode & Sunder (1993). Sends random
  orders around a noisy estimate of the fundamental price.
- MarketMaker: always quotes a bid and an ask around the fundamental, and
  skews its prices according to its inventory.
"""

from __future__ import annotations

import random

from market.orderbook import BUY, SELL, OrderBook


class Agent:
    def __init__(self, agent_id: str, rng: random.Random):
        self.agent_id = agent_id
        self.rng = rng
        self.inventory = 0      # shares held (negative = short)
        self.cash = 0           # in ticks
        self.open_orders: list[tuple[int, int]] = []  # (order_id, step sent)

    def act(self, book: OrderBook, t: int, fundamental: int) -> None:
        raise NotImplementedError

    def on_trade(self, trade) -> None:
        """Updates inventory and cash when one of our orders is filled."""
        if trade.buyer == self.agent_id:
            self.inventory += trade.qty
            self.cash -= trade.qty * trade.price
        if trade.seller == self.agent_id:
            self.inventory -= trade.qty
            self.cash += trade.qty * trade.price

    def pnl(self, mark_price: float) -> float:
        """Profit: cash + inventory marked at the reference price."""
        return self.cash + self.inventory * mark_price


class ZeroIntelligenceTrader(Agent):
    def __init__(self, agent_id, rng, noise=30, max_qty=5,
                 p_market=0.1, order_lifetime=10):
        super().__init__(agent_id, rng)
        self.noise = noise                  # noise on the fundamental estimate (ticks)
        self.max_qty = max_qty
        self.p_market = p_market            # probability of sending a market order
        self.order_lifetime = order_lifetime

    def act(self, book, t, fundamental):
        # 1. Cancel stale orders
        still_open = []
        for oid, sent_at in self.open_orders:
            if t - sent_at >= self.order_lifetime:
                book.cancel(oid)
            else:
                still_open.append((oid, sent_at))
        self.open_orders = still_open

        # 2. Send a new random order
        side = self.rng.choice([BUY, SELL])
        qty = self.rng.randint(1, self.max_qty)
        if self.rng.random() < self.p_market:
            book.submit_market(self.agent_id, side, qty)
        else:
            estimate = fundamental + round(self.rng.gauss(0, self.noise))
            offset = self.rng.randint(1, self.noise)
            price = estimate - offset if side == BUY else estimate + offset
            oid, _ = book.submit_limit(self.agent_id, side, price, qty)
            self.open_orders.append((oid, t))


class MarketMaker(Agent):
    def __init__(self, agent_id, rng, half_spread=10, qty=10,
                 inventory_skew=1, max_inventory=200):
        super().__init__(agent_id, rng)
        self.half_spread = half_spread
        self.qty = qty
        self.inventory_skew = inventory_skew  # price shift per share held
        self.max_inventory = max_inventory

    def act(self, book, t, fundamental):
        # Pull the old quotes and post new ones
        for oid, _ in self.open_orders:
            book.cancel(oid)
        self.open_orders = []

        # Too much inventory -> lower prices to sell, and vice versa
        center = fundamental - self.inventory_skew * self.inventory
        if self.inventory < self.max_inventory:
            oid, _ = book.submit_limit(self.agent_id, BUY, center - self.half_spread, self.qty)
            self.open_orders.append((oid, t))
        if self.inventory > -self.max_inventory:
            oid, _ = book.submit_limit(self.agent_id, SELL, center + self.half_spread, self.qty)
            self.open_orders.append((oid, t))
