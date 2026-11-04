"""
Boucle de simulation : à chaque pas de temps,
1. le prix fondamental bouge (marche aléatoire),
2. chaque agent agit, dans un ordre aléatoire,
3. on enregistre l'état du marché.
"""

from __future__ import annotations

import random

from market.orderbook import OrderBook


def run_simulation(agents, n_steps=500, start_price=10_000,
                   fundamental_vol=5, seed=0):
    rng = random.Random(seed)
    book = OrderBook()
    fundamental = start_price
    agents_by_id = {a.agent_id: a for a in agents}
    history = []

    for t in range(n_steps):
        fundamental += round(rng.gauss(0, fundamental_vol))

        n_trades_before = len(book.trades)
        order = list(agents)
        rng.shuffle(order)
        for agent in order:
            agent.act(book, t, fundamental)

        # Mise à jour des stocks / cash des agents concernés par les trades du pas
        new_trades = book.trades[n_trades_before:]
        for trade in new_trades:
            for aid in {trade.buyer, trade.seller}:
                agents_by_id[aid].on_trade(trade)

        depth = book.depth(levels=5)
        history.append({
            "t": t,
            "fundamental": fundamental,
            "mid": book.mid(),
            "spread": book.spread(),
            "bid_depth": sum(q for _, q in depth["bids"]),
            "ask_depth": sum(q for _, q in depth["asks"]),
            "n_trades": len(new_trades),
            "volume": sum(tr.qty for tr in new_trades),
            "last_price": book.trades[-1].price if book.trades else None,
        })

    return history, book


def summarize(history, agents):
    """Métriques de qualité de marché + profit de chaque agent."""
    valid = [h for h in history if h["mid"] is not None]
    final_mark = history[-1]["fundamental"]
    return {
        "spread_moyen": sum(h["spread"] for h in valid) / len(valid),
        "ecart_moyen_au_fondamental": sum(abs(h["mid"] - h["fundamental"]) for h in valid) / len(valid),
        "volume_total": sum(h["volume"] for h in history),
        "pas_sans_cotation": len(history) - len(valid),
        "pnl": {a.agent_id: round(a.pnl(final_mark)) for a in agents},
    }
