"""
The full experiment: every condition x several seeds, one run after another.
Designed to run overnight:
- runs that already finished are skipped, so if the computer stops, just
  relaunch the same command and it resumes where it left off;
- the cheap control runs (no API) are done first.

Run from the project root (caffeinate keeps the Mac awake):
    caffeinate -i python3 -m experiments.run_grid --model gemma-4-26b-a4b-it
    python3 -m experiments.run_grid --mock          # offline dry run of the whole pipeline

Then analyse:
    python3 -m experiments.analyze
"""

import argparse
import time
from pathlib import Path

from agents.llm_client import DEFAULT_MODEL, GeminiClient, MockClient
from experiments.run_llm import check_api
from experiments.runner import CONDITIONS, run_name, run_one


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    p.add_argument("--conditions", nargs="+", default=list(CONDITIONS), choices=CONDITIONS)
    p.add_argument("--steps", type=int, default=100)
    p.add_argument("--n-llm", type=int, default=3)
    p.add_argument("--act-every", type=int, default=5)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--rpm", type=int, default=15)
    p.add_argument("--mock", action="store_true")
    args = p.parse_args()

    out_root = "results/mock_grid" if args.mock else "results/grid"
    client = MockClient(seed=0) if args.mock else GeminiClient(
        model=args.model, rpm=args.rpm, verbose=False)
    if not args.mock and any(c != "control" for c in args.conditions):
        check_api(client, args.model)

    # control first (instant), then alternate LLM conditions seed by seed,
    # so that a partial night still gives comparable nocomm/comm pairs
    order = [("control", s) for s in args.seeds if "control" in args.conditions]
    order += [(c, s) for s in args.seeds for c in args.conditions if c != "control"]
    todo = [(c, s) for c, s in order if not (Path(out_root) / run_name(c, s) / "summary.json").exists()]

    n_llm_runs = sum(1 for c, _ in todo if c != "control")
    calls = n_llm_runs * args.n_llm * ((args.steps + args.act_every - 1) // args.act_every)
    print(f"{len(order) - len(todo)} runs already done, {len(todo)} to go "
          f"({n_llm_runs} with LLM agents, ~{calls} LLM calls)")

    for i, (condition, seed) in enumerate(todo, 1):
        t0 = time.time()
        print(f"\n[{i}/{len(todo)}] {run_name(condition, seed)} started at {time.strftime('%H:%M')}")
        _, _, stats, _ = run_one(condition, seed, None if condition == "control" else client,
                                 steps=args.steps, n_llm=args.n_llm,
                                 act_every=args.act_every, out_root=out_root)
        print(f"  done in {(time.time() - t0) / 60:.1f} min | spread {stats['mean_spread']:.1f} | "
              f"deviation {stats['mean_abs_deviation_from_fundamental']:.1f} | "
              f"LLM errors {stats['n_llm_errors']}")

    print(f"\nAll runs done. Next: python3 -m experiments.analyze{' --mock' if args.mock else ''}")


if __name__ == "__main__":
    main()
