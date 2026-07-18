"""Ablation: the monolith, with the policy gate bolted on.

The society's benchmark advantage and the policy gate's protection are two
different claims, and juxtaposing them invites a false one. The gate is
architecture-independent: it refuses a forbidden approval no matter who proposed
it, so it would protect a single agent exactly as well as it protects a society.

This module exists so that claim is settled by an experiment rather than by a
disclaimer. It is the monolith — same prompt, same policy, same ledger — with its
decisions passed through `orchestrator._promote()` instead of straight to the
record.

What it isolates:

    monolith          judgment alone      -> how good are the decisions?
    monolith + gate   judgment + policy   -> how much of the safety is the gate?
    society           judgment + policy   -> what do the agents add on top?

If gated-monolith holds the reserve floor too (it does), then the treasury result
is the GATE's, not the society's — and the society's real claim shrinks to the
honest one: it proposes better.
"""
from . import baseline, events, llm, orchestrator, policy


def run_batch(payouts: list[dict], balance: float | None = None,
              reserve_floor: float | None = None) -> dict:
    balance = policy.CURRENT.balance if balance is None else balance
    reserve_floor = policy.CURRENT.reserve_floor if reserve_floor is None else reserve_floor
    events.emit("policy.enacted", "batch", "orchestrator",
                {"version": policy.CURRENT.version, "reason": policy.CURRENT.reason,
                 "params": {**policy.CURRENT.params(), "balance": balance,
                            "reserve_floor": reserve_floor}})
    events.emit("batch.received", "batch", "orchestrator", {"count": len(payouts)})

    result = baseline._decide(payouts, balance, reserve_floor)

    # The monolith's verdicts are PROPOSALS now — exactly like an agent's.
    proposals = {
        d.get("payout_id"): {
            "verdict": "approve" if d.get("action") == "approve" else "reject",
            "proposed_by": "monolith",
            **({"reason": d["reason"]} if d.get("reason") else {}),
        }
        for d in result.get("decisions", [])
    }

    # ...and the same gate decides what may be recorded. No special case for the
    # fact that a single agent produced them.
    orchestrator._promote(payouts, proposals, balance, reserve_floor)

    events.emit("batch.completed", "batch", "orchestrator", {})
    return {
        "state": events.fold_state(),
        "proposals": {pid: p["verdict"] for pid, p in proposals.items()},
        "decisions": result.get("decisions", []),
        "usage": dict(llm.usage_totals),
    }
