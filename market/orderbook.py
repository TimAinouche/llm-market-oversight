"""
Carnet d'ordres (limit order book) avec appariement par priorité prix puis temps.

Conventions :
- Les prix sont des entiers en "ticks" (ex. 10050 = 100,50 €) pour éviter
  les erreurs d'arrondi des floats.
- Un trade s'exécute toujours au prix de l'ordre qui était déjà dans le carnet
  (l'ordre "passif"), comme sur un vrai marché.
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
    side: str              # "buy" ou "sell"
    price: Optional[int]   # None pour un ordre au marché
    qty: int               # quantité restante
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
    # prix -> file d'attente des ordres à ce prix (ordre d'arrivée = priorité temps)
    bids: dict[int, deque] = field(default_factory=dict)
    asks: dict[int, deque] = field(default_factory=dict)
    orders: dict[int, Order] = field(default_factory=dict)  # index pour les annulations
    trades: list[Trade] = field(default_factory=list)
    _ids: count = field(default_factory=lambda: count(1))
    _clock: count = field(default_factory=lambda: count(0))

    # ------------------------------------------------------------------ #
    # Lecture du carnet
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
        """Quantité disponible sur les `levels` meilleurs niveaux de chaque côté."""
        def side_depth(book: dict, reverse: bool):
            prices = sorted(book, reverse=reverse)[:levels]
            return [(p, sum(o.qty for o in book[p])) for p in prices]
        return {"bids": side_depth(self.bids, True), "asks": side_depth(self.asks, False)}

    def snapshot(self, levels: int = 5) -> dict:
        """État du marché sous forme de dict (sera envoyé aux agents LLM en JSON)."""
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

    # ------------------------------------------------------------------ #
    # Envoi d'ordres
    # ------------------------------------------------------------------ #
    def submit_limit(self, agent_id: str, side: str, price: int, qty: int):
        """Ordre limite : s'exécute contre le carnet si possible, le reste
        est placé dans le carnet. Renvoie (order_id, liste des trades)."""
        self._check(side, qty)
        order = Order(next(self._ids), agent_id, side, price, qty, next(self._clock))
        trades = self._match(order)
        if order.qty > 0:
            book = self.bids if side == BUY else self.asks
            book.setdefault(price, deque()).append(order)
            self.orders[order.order_id] = order
        else:
            order.active = False
        return order.order_id, trades

    def submit_market(self, agent_id: str, side: str, qty: int):
        """Ordre au marché : s'exécute au meilleur prix disponible.
        La partie non exécutée (carnet vide) est abandonnée."""
        self._check(side, qty)
        order = Order(next(self._ids), agent_id, side, None, qty, next(self._clock))
        trades = self._match(order)
        order.active = False
        return order.order_id, trades

    def cancel(self, order_id: int) -> bool:
        """Annule un ordre encore dans le carnet. Renvoie False s'il n'existe plus."""
        order = self.orders.pop(order_id, None)
        if order is None or not order.active:
            return False
        order.active = False
        book = self.bids if order.side == BUY else self.asks
        queue = book[order.price]
        queue.remove(order)
        if not queue:
            del book[order.price]
        return True

    # ------------------------------------------------------------------ #
    # Moteur d'appariement
    # ------------------------------------------------------------------ #
    def _match(self, order: Order) -> list[Trade]:
        trades = []
        opposite = self.asks if order.side == BUY else self.bids

        while order.qty > 0 and opposite:
            best = min(opposite) if order.side == BUY else max(opposite)
            # Un ordre limite ne s'exécute que si son prix croise le meilleur prix opposé
            if order.price is not None:
                if order.side == BUY and order.price < best:
                    break
                if order.side == SELL and order.price > best:
                    break

            queue = opposite[best]
            resting = queue[0]                     # priorité temps : le plus ancien
            qty = min(order.qty, resting.qty)
            buy, sell = (order, resting) if order.side == BUY else (resting, order)
            trade = Trade(buy.order_id, sell.order_id, buy.agent_id, sell.agent_id,
                          best, qty, next(self._clock))
            trades.append(trade)
            self.trades.append(trade)

            order.qty -= qty
            resting.qty -= qty
            if resting.qty == 0:
                resting.active = False
                queue.popleft()
                self.orders.pop(resting.order_id, None)
                if not queue:
                    del opposite[best]
        return trades

    @staticmethod
    def _check(side: str, qty: int) -> None:
        if side not in (BUY, SELL):
            raise ValueError(f"side doit être 'buy' ou 'sell', reçu {side!r}")
        if qty <= 0:
            raise ValueError("la quantité doit être positive")
