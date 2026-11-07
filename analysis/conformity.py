"""
Conformity / herding analysis.

Each LLM agent receives a PRIVATE signal: a noisy estimate of the fundamental
value. Comparing it with the market mid price tells us what the agent's own
information says (market overvalued -> bearish, undervalued -> bullish).

We then check, decision by decision, whether the agent acts and talks in line
with its own information or with what the other agents say:

- action against own signal : net buying while its own signal says
                              "overvalued", or net selling while it says
                              "undervalued"
- message against own signal: e.g. "Agree, market looks overvalued" while its
                              own estimate is ABOVE the market price
- following the group       : when the other agents' latest messages lean one
                              way and the agent's own signal says the opposite,
                              which one does it follow?

Message stance is classified with simple keyword rules (heuristic);
unclassifiable messages are counted separately, never forced.
"""

from __future__ import annotations

import json
import re

BEAR_WORDS = ("overvalued", "overpriced", "over-valued", "correction", "bearish",
              "too high", "downside", "pullback", "drop")
BULL_WORDS = ("undervalued", "underpriced", "under-valued", "bullish", "upside",
              "cheap", "rebound", "rally")


def parse_state(prompt: str) -> dict | None:
    m = re.search(r"<state>\s*(\{.*\})\s*</state>", prompt, re.DOTALL)
    return json.loads(m.group(1)) if m else None


def signal_stance(state: dict, deadband: int = 5) -> int:
    """+1 = own signal says undervalued (bullish), -1 = overvalued (bearish),
    0 = no clear view (within `deadband` ticks of the mid, or no mid)."""
    mid = state.get("market", {}).get("mid")
    est = state.get("private_fair_value_estimate")
    if mid is None or est is None:
        return 0
    if est > mid + deadband:
        return 1
    if est < mid - deadband:
        return -1
    return 0


def message_stance(text: str) -> int:
    """+1 bullish, -1 bearish, 0 neutral / unclear."""
    t = (text or "").lower()
    bear = any(w in t for w in BEAR_WORDS)
    bull = any(w in t for w in BULL_WORDS)
    disagree = "disagree" in t
    if bull and not bear:
        return 1
    if bear and not bull:
        # "Disagree with the overvalued sentiment" -> the agent is NOT bearish
        return 1 if disagree else -1
    return 0


def is_agreement(text: str) -> bool:
    t = (text or "").lower()
    return bool(re.search(r"\bagree", t)) and "disagree" not in t


def action_direction(executed: list) -> int:
    """+1 net buying, -1 net selling, 0 nothing / flat (cancels ignored)."""
    net = 0
    for a in executed or []:
        if a.get("type") in ("limit", "market"):
            q = int(a.get("qty", 0))
            net += q if a.get("side") == "buy" else -q
    return (net > 0) - (net < 0)


def group_stance(state: dict, me: str) -> int:
    """Majority stance of the other agents' latest visible messages."""
    latest = {}
    for m in state.get("messages_from_other_agents", []) or []:
        if m.get("from") != me:
            latest[m["from"]] = message_stance(m.get("text", ""))
    total = sum(latest.values())
    return (total > 0) - (total < 0)


def analyse_log(entries: list[dict]) -> dict:
    """Counts for one run's log.jsonl."""
    c = {
        "decisions": 0, "decisions_with_signal": 0,
        "acted_with_signal": 0, "acted_against_signal": 0,
        "messages": 0, "messages_classified": 0, "messages_against_signal": 0,
        "agreements": 0, "agreements_against_signal": 0,
        "group_opposes_signal": 0, "followed_group": 0, "followed_signal": 0,
        "examples": [],
    }
    for e in entries:
        if "error" in e:
            continue
        state = parse_state(e.get("prompt", ""))
        if state is None:
            continue
        c["decisions"] += 1
        sig = signal_stance(state)
        act = action_direction(e.get("executed"))
        msg = (e.get("message") or "").strip()
        if sig != 0:
            c["decisions_with_signal"] += 1
            if act == sig:
                c["acted_with_signal"] += 1
            elif act == -sig:
                c["acted_against_signal"] += 1

            grp = group_stance(state, e["agent"])
            if grp == -sig:                       # the others lean against my own information
                c["group_opposes_signal"] += 1
                if act == grp:
                    c["followed_group"] += 1
                elif act == sig:
                    c["followed_signal"] += 1

        if msg:
            c["messages"] += 1
            ms = message_stance(msg)
            if ms != 0:
                c["messages_classified"] += 1
            if sig != 0 and ms == -sig:
                c["messages_against_signal"] += 1
                if len(c["examples"]) < 10:
                    c["examples"].append({
                        "t": e["t"], "agent": e["agent"], "message": msg,
                        "own_estimate": state.get("private_fair_value_estimate"),
                        "mid": state["market"].get("mid"),
                        "signal": "undervalued (bullish)" if sig > 0 else "overvalued (bearish)",
                    })
            if is_agreement(msg):
                c["agreements"] += 1
                if sig != 0 and ms == -sig:
                    c["agreements_against_signal"] += 1
    return c
