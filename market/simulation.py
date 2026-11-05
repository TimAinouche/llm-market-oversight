"""
Simulation loop. At each time step:
1. the fundamental price moves (random walk),
2. every agent acts, in a random order,
3. the market state is recorded.
"""

from __future__ import annotations

import random

from market.orderbook import OrderBook


def run_simulation(agents, n_steps=500, start_price=10_000,
                   fundamental_vol=5, seed=0, on_step=None):
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

        # Update inventory / cash of the agents involved in this step's trades
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
        if on_step is not None:
            on_step(t, n_steps)

    return history, book


def summarize(history, agents):
    """Market-quality metrics + profit of each agent."""
    valid = [h for h in history if h["mid"] is not None]
    final_mark = history[-1]["fundamental"]
    return {
        "mean_spread": sum(h["spread"] for h in valid) / len(valid),
        "mean_abs_deviation_from_fundamental":
            sum(abs(h["mid"] - h["fundamental"]) for h in valid) / len(valid),
        "total_volume": sum(h["volume"] for h in history),
        "steps_without_quotes": len(history) - len(valid),
        "pnl": {a.agent_id: round(a.pnl(final_mark)) for a in agents},
    }
