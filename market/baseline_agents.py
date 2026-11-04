"""
Agents de référence (non-LLM).

Ils servent de point de comparaison : si un comportement apparaît avec des
agents LLM mais pas avec ces agents simples, on peut l'attribuer aux LLM.

- ZeroIntelligenceTrader : inspiré de Gode & Sunder (1993). Envoie des ordres
  aléatoires autour d'une estimation bruitée du prix fondamental.
- MarketMaker : affiche en permanence un prix d'achat et un prix de vente
  autour du fondamental, et décale ses prix selon son stock (inventaire).
"""

from __future__ import annotations

import random

from market.orderbook import BUY, SELL, OrderBook


class Agent:
    def __init__(self, agent_id: str, rng: random.Random):
        self.agent_id = agent_id
        self.rng = rng
        self.inventory = 0      # nombre de titres détenus (négatif = vendeur à découvert)
        self.cash = 0           # en ticks
        self.open_orders: list[tuple[int, int]] = []  # (order_id, pas de temps d'envoi)

    def act(self, book: OrderBook, t: int, fundamental: int) -> None:
        raise NotImplementedError

    def on_trade(self, trade) -> None:
        """Met à jour stock et cash quand un de nos ordres est exécuté."""
        if trade.buyer == self.agent_id:
            self.inventory += trade.qty
            self.cash -= trade.qty * trade.price
        if trade.seller == self.agent_id:
            self.inventory -= trade.qty
            self.cash += trade.qty * trade.price

    def pnl(self, mark_price: float) -> float:
        """Profit : cash + valeur du stock au prix de référence."""
        return self.cash + self.inventory * mark_price


class ZeroIntelligenceTrader(Agent):
    def __init__(self, agent_id, rng, noise=30, max_qty=5,
                 p_market=0.1, order_lifetime=10):
        super().__init__(agent_id, rng)
        self.noise = noise                  # bruit sur l'estimation du fondamental (ticks)
        self.max_qty = max_qty
        self.p_market = p_market            # probabilité d'envoyer un ordre au marché
        self.order_lifetime = order_lifetime

    def act(self, book, t, fundamental):
        # 1. Annuler les ordres trop anciens
        still_open = []
        for oid, sent_at in self.open_orders:
            if t - sent_at >= self.order_lifetime:
                book.cancel(oid)
            else:
                still_open.append((oid, sent_at))
        self.open_orders = still_open

        # 2. Envoyer un nouvel ordre aléatoire
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
        self.inventory_skew = inventory_skew  # décalage de prix par titre en stock
        self.max_inventory = max_inventory

    def act(self, book, t, fundamental):
        # Retire ses anciennes cotations et en affiche de nouvelles
        for oid, _ in self.open_orders:
            book.cancel(oid)
        self.open_orders = []

        # Trop de stock -> baisse ses prix pour vendre, et inversement
        center = fundamental - self.inventory_skew * self.inventory
        if self.inventory < self.max_inventory:
            oid, _ = book.submit_limit(self.agent_id, BUY, center - self.half_spread, self.qty)
            self.open_orders.append((oid, t))
        if self.inventory > -self.max_inventory:
            oid, _ = book.submit_limit(self.agent_id, SELL, center + self.half_spread, self.qty)
            self.open_orders.append((oid, t))
