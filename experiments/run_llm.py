"""
LLM experiment: the baseline market (1 market maker + 3 zero-intelligence
traders) plus 3 LLM trading agents.

Run from the project root:
    python3 -m experiments.run_llm --mock              # offline dry run, no API
    python3 -m experiments.run_llm                     # real run, no communication
    python3 -m experiments.run_llm --comm              # real run, agents can talk

Outputs:
    results/<run_name>/log.jsonl     every LLM decision (prompt, reasoning, actions)
    results/<run_name>/summary.json  market metrics and profits
    figures/<run_name>.png           price vs fundamental, spread
"""

import argparse
import json
import random
from pathlib import Path

from agents.llm_client import DEFAULT_MODEL, GeminiClient, MockClient
from agents.llm_trader import LLMTrader, MessageBoard
from experiments.run_baseline import plot_market
from market.baseline_agents import MarketMaker, ZeroIntelligenceTrader
from market.simulation import run_simulation, summarize


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=100)
    p.add_argument("--n-llm", type=int, default=3)
    p.add_argument("--act-every", type=int, default=5)
    p.add_argument("--comm", action="store_true", help="LLM agents can message each other")
    p.add_argument("--mock", action="store_true", help="use the fake LLM (no API calls)")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--rpm", type=int, default=15, help="max LLM calls per minute (free tier limit)")
    args = p.parse_args()

    rng = random.Random(args.seed)
    client = MockClient(seed=args.seed) if args.mock else GeminiClient(model=args.model, rpm=args.rpm)
    board = MessageBoard() if args.comm else None

    if not args.mock:  # fail fast on a bad key or model name, before the long run
        try:
            client.generate("Reply with the single word OK.")
        except Exception as e:
            raise SystemExit(f"API check failed: {e}\n"
                             "Check GEMINI_API_KEY in .env and the model name "
                             "(list them with: python3 -m agents.llm_client)")
        print(f"API OK, model: {args.model}")

    agents = [MarketMaker("MM", rng)]
    agents += [ZeroIntelligenceTrader(f"ZI_{i}", rng) for i in range(3)]
    llm_agents = [
        LLMTrader(f"LLM_{i}", rng, client, act_every=args.act_every, board=board)
        for i in range(args.n_llm)
    ]
    agents += llm_agents

    n_calls = args.n_llm * ((args.steps + args.act_every - 1) // args.act_every)
    condition = "comm" if args.comm else "nocomm"
    run_name = f"{'mock' if args.mock else 'llm'}_{condition}_seed{args.seed}"
    print(f"Run {run_name}: {args.steps} steps, ~{n_calls} LLM calls")
    if not args.mock:
        print(f"Expected duration: at least {n_calls / args.rpm:.0f} min (max {args.rpm} calls/min)")

    def progress(t, n):
        if (t + 1) % 10 == 0:
            print(f"  step {t + 1}/{n}")

    history, _ = run_simulation(agents, n_steps=args.steps, seed=args.seed, on_step=progress)
    stats = summarize(history, agents)

    out = Path("results") / run_name
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "log.jsonl", "w") as f:
        for agent in llm_agents:
            for entry in agent.log:
                f.write(json.dumps(entry) + "\n")
    stats["n_llm_errors"] = sum(1 for a in llm_agents for e in a.log if "error" in e)
    stats["n_rejected_actions"] = sum(len(e.get("rejected", [])) for a in llm_agents for e in a.log)
    stats["config"] = vars(args)
    (out / "summary.json").write_text(json.dumps(stats, indent=2))

    print(f"\n=== {run_name} ===")
    for k, v in stats.items():
        if k != "config":
            print(f"{k}: {v}")

    fig_path = f"figures/{run_name}.png"
    plot_market(history, f"Market with {args.n_llm} LLM agents ({'communication' if args.comm else 'no communication'})", fig_path)
    print(f"\nLog: {out / 'log.jsonl'}\nFigure: {fig_path}")

    # A few reasoning samples, to read what the agents are thinking
    print("\n--- Sample reasoning ---")
    for agent in llm_agents:
        for e in agent.log[:2]:
            print(f"[t={e['t']}] {agent.agent_id}: {e.get('reasoning') or e.get('error')}")
            if e.get("error") and e.get("finish_reason"):
                print(f"    finish_reason: {e['finish_reason']}")
            if e.get("message"):
                print(f"    message: {e['message']}")


if __name__ == "__main__":
    main()
