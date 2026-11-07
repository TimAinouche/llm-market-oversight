"""
Runs ONE experiment, to try things out.

Run from the project root:
    python3 -m experiments.run_llm --mock              # offline dry run, no API
    python3 -m experiments.run_llm                     # LLM agents, no communication
    python3 -m experiments.run_llm --comm              # LLM agents can talk

For the full experiment (all conditions x several seeds), use run_grid.py.
"""

import argparse

from agents.llm_client import DEFAULT_MODEL, GeminiClient, MockClient
from experiments.run_baseline import plot_market
from experiments.runner import run_one


def check_api(client, model):
    """Fails fast on a bad key or model name, before a long run."""
    try:
        client.generate("Reply with the single word OK.")
    except Exception as e:
        raise SystemExit(f"API check failed: {e}\n"
                         "Check GEMINI_API_KEY in .env and the model name "
                         "(list them with: python3 -m agents.llm_client)")
    print(f"API OK, model: {model}")


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

    client = MockClient(seed=args.seed) if args.mock else GeminiClient(model=args.model, rpm=args.rpm)
    if not args.mock:
        check_api(client, args.model)

    condition = "comm" if args.comm else "nocomm"
    out_root = "results/mock" if args.mock else "results/single"
    out, history, stats, llm_agents = run_one(
        condition, args.seed, client, steps=args.steps, n_llm=args.n_llm,
        act_every=args.act_every, out_root=out_root)

    print(f"\n=== {condition}, seed {args.seed} ===")
    for k, v in stats.items():
        if k != "config":
            print(f"{k}: {v}")

    prefix = "mock" if args.mock else "llm"
    fig_path = f"figures/{prefix}_{condition}_seed{args.seed}.png"
    plot_market(history, f"Market with {args.n_llm} LLM agents "
                         f"({'communication' if args.comm else 'no communication'})", fig_path)
    print(f"\nResults: {out}\nFigure: {fig_path}")

    print("\n--- Sample reasoning ---")
    for agent in llm_agents:
        for e in agent.log[:2]:
            print(f"[t={e['t']}] {agent.agent_id}: {e.get('reasoning') or e.get('error')}")
            if e.get("message"):
                print(f"    message: {e['message']}")


if __name__ == "__main__":
    main()
