"""
Expérience de référence : un market maker + 5 traders "zero-intelligence".

Lancer depuis la racine du projet :
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


def main():
    agents = build_agents(SEED)
    history, _ = run_simulation(agents, n_steps=500, seed=SEED)
    stats = summarize(history, agents)

    print("=== Marché de référence (sans LLM) ===")
    for k, v in stats.items():
        print(f"{k}: {v}")

    t = [h["t"] for h in history]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    ax1.plot(t, [h["fundamental"] / 100 for h in history], label="Prix fondamental", color="#888888")
    ax1.plot(t, [h["mid"] / 100 if h["mid"] else None for h in history], label="Prix milieu (mid)", color="#2563eb")
    ax1.set_ylabel("Prix (€)")
    ax1.legend()
    ax2.plot(t, [h["spread"] / 100 if h["spread"] else None for h in history], color="#dc2626")
    ax2.set_ylabel("Spread (€)")
    ax2.set_xlabel("Pas de temps")
    fig.suptitle("Marché de référence : 1 market maker + 5 traders zero-intelligence")
    fig.tight_layout()

    out = Path("figures")
    out.mkdir(exist_ok=True)
    fig.savefig(out / "baseline.png", dpi=120)
    print(f"Graphique enregistré dans {out / 'baseline.png'}")


if __name__ == "__main__":
    main()
