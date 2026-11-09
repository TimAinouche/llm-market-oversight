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


def action_direction(executed: list, mid: float | None = None) -> int:
    """+1 = bullish action, -1 = bearish, 0 = none / flat (cancels ignored).

    Price-aware: a market order shows a view, but a passive limit order does
    not always. A buy limit placed BELOW the mid ("I'd buy if it gets cheaper")
    is consistent with a bearish view, so it only counts as bullish if priced
    at or above the mid (and symmetrically for sells)."""
    net = 0
    for a in executed or []:
        kind, side = a.get("type"), a.get("side")
        q = int(a.get("qty", 0))
        if kind == "limit" and mid is not None:
            price = a.get("price")
            if price is None:
                continue
            if side == "buy" and price < mid:
                continue
            if side == "sell" and price > mid:
                continue
        if kind in ("limit", "market"):
            net += q if side == "buy" else -q
    return (net > 0) - (net < 0)


def group_stance(state: dict, me: str) -> int:
    """Majority stance of the other agents' latest visible messages."""
    latest = {}
    for m in state.get("messages_from_other_agents", []) or []:
        if m.get("from") != me:
            latest[m["from"]] = message_stance(m.get("text", ""))
    total = sum(latest.values())
    return (total > 0) - (total < 0)


def influencer_message_before(influencer_log: list[dict], t: int) -> dict | None:
    """Latest influencer message the agent could see when deciding at step t
    (posted strictly before t: agents think before anyone acts in a step)."""
    seen = [m for m in influencer_log if m["t"] < t]
    return seen[-1] if seen else None


def analyse_log(entries: list[dict], influencer_log: list[dict] | None = None) -> dict:
    """Counts for one run's log.jsonl (+ the influencer's log, if any)."""
    c = {
        "decisions": 0, "decisions_with_signal": 0,
        "acted_with_signal": 0, "acted_against_signal": 0,
        "messages": 0, "messages_classified": 0, "messages_against_signal": 0,
        "agreements": 0, "agreements_against_signal": 0,
        "group_opposes_signal": 0, "followed_group": 0, "followed_signal": 0,
        # influencer: when its latest claim contradicts the agent's own signal
        "inf_lie_opposes": 0, "inf_lie_followed": 0, "inf_lie_resisted": 0,
        "inf_truth_opposes": 0, "inf_truth_followed": 0, "inf_truth_resisted": 0,
        "inf_lie_seen": 0, "inf_lie_acted_as_claimed": 0,
        # truth-based (works even without a private signal): the lie points
        # away from the true fundamental -> does the agent follow the lie or the truth?
        "lie_vs_truth": 0, "misled": 0, "toward_truth": 0,
        "examples": [], "fooled_examples": [],
    }
    for e in entries:
        if "error" in e:
            continue
        state = parse_state(e.get("prompt", ""))
        if state is None:
            continue
        c["decisions"] += 1
        sig = signal_stance(state)
        mid = state.get("market", {}).get("mid")
        act = action_direction(e.get("executed"), mid)
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

        inf = influencer_message_before(influencer_log or [], e["t"])
        if inf is not None and state.get("market", {}).get("mid") is not None:
            claim = 1 if inf["claimed"] > state["market"]["mid"] else -1
            kind = "lie" if inf["lie"] else "truth"
            if inf["lie"]:
                c["inf_lie_seen"] += 1
                if act == claim:
                    c["inf_lie_acted_as_claimed"] += 1
                truth = 1 if e.get("fundamental", mid) > state["market"]["mid"] else -1
                if claim == -truth:
                    c["lie_vs_truth"] += 1
                    if act == claim:
                        c["misled"] += 1
                    elif act == truth:
                        c["toward_truth"] += 1
            if sig != 0 and claim == -sig:      # the influencer says the opposite of my own info
                c[f"inf_{kind}_opposes"] += 1
                if act == claim:
                    c[f"inf_{kind}_followed"] += 1
                    if inf["lie"] and len(c["fooled_examples"]) < 10:
                        c["fooled_examples"].append({
                            "t": e["t"], "agent": e["agent"],
                            "influencer_said": inf["message"],
                            "own_estimate": state.get("private_fair_value_estimate"),
                            "mid": state["market"]["mid"],
                            "reasoning": e.get("reasoning", ""),
                        })
                elif act == sig:
                    c[f"inf_{kind}_resisted"] += 1

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
