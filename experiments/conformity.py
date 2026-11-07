"""
Herding / conformity analysis on the finished grid runs (no new API calls).

Run from the project root:
    python3 -m experiments.conformity

Outputs:
    reports/conformity.md      results + examples of messages against own information
    figures/conformity.png
"""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from analysis.conformity import analyse_log

CONDS = ("nocomm", "comm", "liar", "mixed", "authority")


def rate(a, b):
    return a / b if b else float("nan")


def pct(a, b):
    return f"{100 * a / b:.0f}% ({a}/{b})" if b else "-"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="results/grid")
    p.add_argument("--reports", default="reports")
    args = p.parse_args()

    root = Path(args.root)
    per_run = {}
    for d in sorted(root.glob("*")):
        cond = d.name.split("_seed")[0]
        if cond not in CONDS or not (d / "summary.json").exists():
            continue
        entries = [json.loads(l) for l in (d / "log.jsonl").read_text().splitlines() if l.strip()]
        inf_path = d / "influencer.jsonl"
        inf_log = ([json.loads(l) for l in inf_path.read_text().splitlines() if l.strip()]
                   if inf_path.exists() else None)
        per_run[d.name] = (cond, analyse_log(entries, inf_log))
    if not per_run:
        raise SystemExit(f"No finished LLM runs in {root}.")

    totals = {}
    for cond, c in per_run.values():
        t = totals.setdefault(cond, {k: ([] if isinstance(v, list) else 0) for k, v in c.items()})
        for k, v in c.items():
            t[k] += v

    present = [c for c in CONDS if c in totals]
    lines = ["# Conformity / herding analysis", "",
             "Each LLM agent gets a private, noisy estimate of the fundamental value. "
             "Its **own signal** is bearish when that estimate is below the market mid price "
             "(market overvalued for this agent) and bullish when it is above "
             "(5-tick dead band: no clear signal in between).", "",
             "| | " + " | ".join(present) + " |", "|---|" + "---|" * len(present)]
    rows = [
        ("Decisions analysed", lambda t: str(t["decisions"])),
        ("Decisions with a clear own signal", lambda t: str(t["decisions_with_signal"])),
        ("Net trade WITH own signal", lambda t: pct(t["acted_with_signal"], t["decisions_with_signal"])),
        ("Net trade AGAINST own signal", lambda t: pct(t["acted_against_signal"], t["decisions_with_signal"])),
        ("Messages sent", lambda t: str(t["messages"])),
        ("Messages stating a view against own signal", lambda t: pct(t["messages_against_signal"], t["messages"])),
        ("'Agree' messages against own signal", lambda t: pct(t["agreements_against_signal"], t["agreements"])),
        ("Others' messages lean against own signal", lambda t: str(t["group_opposes_signal"])),
        ("  ... agent then trades with the group", lambda t: pct(t["followed_group"], t["group_opposes_signal"])),
        ("  ... agent then trades with its own signal", lambda t: pct(t["followed_signal"], t["group_opposes_signal"])),
        ("**Influencer**: decisions after a LIE", lambda t: str(t["inf_lie_seen"])),
        ("  ... agent trades in the direction of the lie", lambda t: pct(t["inf_lie_acted_as_claimed"], t["inf_lie_seen"])),
        ("Lie contradicts the agent's own signal", lambda t: str(t["inf_lie_opposes"])),
        ("  ... agent follows the lie (fooled)", lambda t: pct(t["inf_lie_followed"], t["inf_lie_opposes"])),
        ("  ... agent follows its own signal (resisted)", lambda t: pct(t["inf_lie_resisted"], t["inf_lie_opposes"])),
        ("True influencer info contradicts own signal", lambda t: str(t["inf_truth_opposes"])),
        ("  ... agent follows the influencer", lambda t: pct(t["inf_truth_followed"], t["inf_truth_opposes"])),
    ]
    for label, f in rows:
        lines.append(f"| {label} | " + " | ".join(
            f(totals[c]) for c in present) + " |")

    lines += ["", "Totals over all seeds. Message stance is classified with keyword rules "
              "(heuristic); messages with no clear stance are not counted as against.", "",
              "## Messages stating a view against the agent's own information", ""]
    ex = totals.get("comm", {}).get("examples", [])
    if not ex:
        lines.append("None found.")
    for x in ex[:10]:
        lines.append(f"- t={x['t']} **{x['agent']}**: \"{x['message']}\" — own estimate "
                     f"{x['own_estimate']} vs mid {x['mid']} → own signal: {x['signal']}")

    lines += ["", "## Agents fooled by the influencer (traded with the lie, against their own information)", ""]
    fooled = [x for c in ("liar", "mixed", "authority") if c in totals for x in totals[c]["fooled_examples"]]
    if not fooled:
        lines.append("None found.")
    for x in fooled[:10]:
        lines.append(f"- t={x['t']} **{x['agent']}** — influencer said: \"{x['influencer_said']}\" — "
                     f"own estimate {x['own_estimate']} vs mid {x['mid']} — reasoning: \"{x['reasoning']}\"")

    reports = Path(args.reports)
    reports.mkdir(exist_ok=True)
    (reports / "conformity.md").write_text("\n".join(lines) + "\n")

    # Figure: share of decisions where the agent trades against its own signal, per run
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = {"nocomm": "#2563eb", "comm": "#dc2626", "liar": "#9333ea", "mixed": "#f59e0b",
              "authority": "#0f766e"}
    for i, cond in enumerate(present):
        vals = [rate(c["acted_against_signal"], c["decisions_with_signal"])
                for cnd, c in per_run.values() if cnd == cond]
        if vals:
            ax.bar(i, sum(vals) / len(vals), color=colors[cond], alpha=0.8)
            ax.scatter([i] * len(vals), vals, color="black", s=15, zorder=3)
    ax.set_xticks(range(len(present)), present)
    ax.set_ylabel("Share of decisions")
    ax.set_title("LLM agents trading AGAINST their own private signal")
    fig.tight_layout()
    fig.savefig("figures/conformity.png", dpi=120)

    print("\n".join(lines))
    print(f"\nSaved: {reports / 'conformity.md'}, figures/conformity.png")


if __name__ == "__main__":
    main()
