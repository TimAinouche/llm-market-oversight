import random

from market.baseline_agents import MarketMaker, ZeroIntelligenceTrader
from market.simulation import run_simulation, summarize


def make_agents(seed=1):
    rng = random.Random(seed)
    return [MarketMaker("MM", rng)] + [ZeroIntelligenceTrader(f"ZI_{i}", rng) for i in range(3)]


def test_la_simulation_tourne_et_produit_des_trades():
    agents = make_agents()
    history, book = run_simulation(agents, n_steps=100, seed=1)
    assert len(history) == 100
    assert sum(h["volume"] for h in history) > 0


def test_meme_graine_meme_resultat():
    h1, _ = run_simulation(make_agents(), n_steps=50, seed=3)
    h2, _ = run_simulation(make_agents(), n_steps=50, seed=3)
    assert h1 == h2


def test_les_stocks_s_equilibrent():
    # Chaque titre acheté par un agent est vendu par un autre : la somme des stocks vaut 0
    agents = make_agents()
    run_simulation(agents, n_steps=200, seed=5)
    assert sum(a.inventory for a in agents) == 0
    assert sum(a.cash for a in agents) == 0


def test_le_market_maker_garde_le_prix_proche_du_fondamental():
    agents = make_agents()
    history, _ = run_simulation(agents, n_steps=300, seed=7)
    stats = summarize(history, agents)
    assert stats["ecart_moyen_au_fondamental"] < 50   # moins de 0,50 €
