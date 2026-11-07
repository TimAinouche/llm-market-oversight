"""
Runs one experiment (one condition, one seed) and saves everything needed for
the analysis and for the monitor.

Conditions:
- control : the LLM agents are replaced by zero-intelligence traders (no API)
- nocomm  : 3 LLM agents, no communication
- comm    : 3 LLM agents that can post messages to each other
- liar    : comm + a scripted influencer who lies in every message
- mixed   : comm + a scripted influencer who builds credibility with true
            information, then mixes truth and lies
- authority: same lies as "liar", presented with a prestigious professional title

Every run has the same market around the agents: 1 market maker + 3
zero-intelligence traders.

Saved in results/<condition>_seed<seed>/:
    summary.json   market metrics, profits, config
    history.json   market state at every step
    events.jsonl   every order, cancel and trade (audit trail)
    log.jsonl      every LLM decision: prompt, thoughts, reasoning, actions, message
    influencer.jsonl  every influencer message, with the truth (liar / mixed only)
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

from agents.influencer import INFLUENCER_ID, Influencer
from agents.llm_trader import LLMTrader, MessageBoard
from market.baseline_agents import MarketMaker, ZeroIntelligenceTrader
from market.simulation import run_simulation, summarize

CONDITIONS = ("control", "nocomm", "comm", "liar", "mixed", "authority")


def run_name(condition: str, seed: int) -> str:
    return f"{condition}_seed{seed}"


def build_agents(condition, seed, client, n_llm=3, act_every=5):
    """Returns (all agents, LLM agents, influencer or None)."""
    rng = random.Random(seed)
    agents = [MarketMaker("MM", rng)]
    agents += [ZeroIntelligenceTrader(f"ZI_{i}", rng) for i in range(3)]
    if condition == "control":
        # same number of extra traders, but without any intelligence
        agents += [ZeroIntelligenceTrader(f"CTRL_{i}", rng) for i in range(n_llm)]
        return agents, [], None
    board = MessageBoard() if condition != "nocomm" else None
    # each LLM agent gets its own random generator: they think in parallel threads
    llm_agents = [
        LLMTrader(f"LLM_{i}", random.Random(seed * 1000 + i), client,
                  act_every=act_every, board=board)
        for i in range(n_llm)
    ]
    influencer = None
    if condition in ("liar", "mixed", "authority"):
        influencer = Influencer(INFLUENCER_ID, random.Random(seed * 7919), board,
                                profile=condition, act_every=act_every)
        agents.append(influencer)
    return agents + llm_agents, llm_agents, influencer


def run_one(condition, seed, client=None, steps=100, n_llm=3, act_every=5,
            out_root="results", verbose=True):
    assert condition in CONDITIONS, condition
    agents, llm_agents, influencer = build_agents(condition, seed, client, n_llm, act_every)
    name = run_name(condition, seed)

    def progress(t, n):
        if verbose and (t + 1) % 10 == 0:
            print(f"  [{name}] step {t + 1}/{n}")

    start = time.time()
    history, book = run_simulation(agents, n_steps=steps, seed=seed, on_step=progress)
    stats = summarize(history, agents)
    stats["n_llm_errors"] = sum(1 for a in llm_agents for e in a.log if "error" in e)
    stats["n_rejected_actions"] = sum(len(e.get("rejected", [])) for a in llm_agents for e in a.log)
    stats["config"] = {
        "condition": condition, "seed": seed, "steps": steps, "n_llm": n_llm,
        "act_every": act_every, "model": getattr(client, "model", "mock" if client else None),
        "duration_min": round((time.time() - start) / 60, 1),
    }

    out = Path(out_root) / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "history.json").write_text(json.dumps(history))
    with open(out / "events.jsonl", "w") as f:
        for ev in book.events:
            f.write(json.dumps(ev) + "\n")
    with open(out / "log.jsonl", "w") as f:
        for agent in llm_agents:
            for entry in agent.log:
                f.write(json.dumps(entry) + "\n")
    if influencer is not None:
        with open(out / "influencer.jsonl", "w") as f:
            for entry in influencer.log:
                f.write(json.dumps(entry) + "\n")
    # summary.json is written last: its presence means the run completed
    (out / "summary.json").write_text(json.dumps(stats, indent=2))
    return out, history, stats, llm_agents
