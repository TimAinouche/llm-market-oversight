import random

from market.baseline_agents import MarketMaker, ZeroIntelligenceTrader
from market.simulation import run_simulation, summarize


def make_agents(seed=1):
    rng = random.Random(seed)
    return [MarketMaker("MM", rng)] + [ZeroIntelligenceTrader(f"ZI_{i}", rng) for i in range(3)]


def test_simulation_runs_and_produces_trades():
    agents = make_agents()
    history, book = run_simulation(agents, n_steps=100, seed=1)
    assert len(history) == 100
    assert sum(h["volume"] for h in history) > 0


def test_same_seed_same_result():
    h1, _ = run_simulation(make_agents(), n_steps=50, seed=3)
    h2, _ = run_simulation(make_agents(), n_steps=50, seed=3)
    assert h1 == h2


def test_inventories_and_cash_net_to_zero():
    # Every share bought by one agent is sold by another: totals must be 0
    agents = make_agents()
    run_simulation(agents, n_steps=200, seed=5)
    assert sum(a.inventory for a in agents) == 0
    assert sum(a.cash for a in agents) == 0


def test_market_maker_keeps_price_close_to_fundamental():
    agents = make_agents()
    history, _ = run_simulation(agents, n_steps=300, seed=7)
    stats = summarize(history, agents)
    assert stats["mean_abs_deviation_from_fundamental"] < 50   # less than EUR 0.50
