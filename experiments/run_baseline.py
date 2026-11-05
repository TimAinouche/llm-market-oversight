"""
Baseline experiment: one market maker + 5 zero-intelligence traders.

Run from the project root:
    python3 -m experiments.run_baseline
"""

import random
from pathlib import Path

import matplotlib.pyplot as plt

from market.baseline_agents import MarketMaker, ZeroIntelligenceTrader
from market.simulation import run_simulation, summarize

SEED = 42


def build_agents(seed):
    rng = random.Random(seed)
    agents = [MarketMaker("MM", rng)]
    agents += [ZeroIntelligenceTrader(f"ZI_{i}", rng) for i in range(5)]
    return agents


def plot_market(history, title, path):
    t = [h["t"] for h in history]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    ax1.plot(t, [h["fundamental"] / 100 for h in history], label="Fundamental price", color="#888888")
    ax1.plot(t, [h["mid"] / 100 if h["mid"] else None for h in history], label="Mid price", color="#2563eb")
    ax1.set_ylabel("Price (EUR)")
    ax1.legend()
    ax2.plot(t, [h["spread"] / 100 if h["spread"] else None for h in history], color="#dc2626")
    ax2.set_ylabel("Spread (EUR)")
    ax2.set_xlabel("Time step")
    fig.suptitle(title)
    fig.tight_layout()
    Path(path).parent.mkdir(exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    agents = build_agents(SEED)
    history, _ = run_simulation(agents, n_steps=500, seed=SEED)
    stats = summarize(history, agents)

    print("=== Baseline market (no LLM) ===")
    for k, v in stats.items():
        print(f"{k}: {v}")

    path = "figures/baseline.png"
    plot_market(history, "Baseline market: 1 market maker + 5 zero-intelligence traders", path)
    print(f"Figure saved to {path}")


if __name__ == "__main__":
    main()
