"""Society orchestrator: task decomposition, role routing, conflict resolution."""
from concurrent.futures import ThreadPoolExecutor

from . import agents, anchor, events, policy


def run_batch(payouts: list[dict], balance: float = policy.BALANCE, reserve_floor: float = policy.RESERVE_FLOOR) -> dict:
    # policy is history too: record which version governs this batch, so any
    # replay knows exactly what the rules were at decision time
    events.emit("policy.enacted", "batch", "orchestrator",
                {"version": policy.CURRENT.version, "reason": policy.CURRENT.reason,
                 "params": {**policy.CURRENT.params(), "balance": balance,
                            "reserve_floor": reserve_floor}})
    events.emit("batch.received", "batch", "orchestrator", {"count": len(payouts)})

    # 1. Decompose: intake triages every request (cheap model, in parallel)
    with ThreadPoolExecutor(max_workers=8) as pool:
        triage = list(pool.map(agents.intake, payouts))
    triaged = list(zip(payouts, triage))

    # 2. Route by risk tier: low-risk skips deep compliance review
    cleared, vetoed = [], []
    for payout, tri in triaged:
        if tri.get("risk_tier") == "low":
            events.emit("compliance.fast_tracked", payout["id"], "orchestrator", {})
            cleared.append(payout)
            continue
        verdict = agents.compliance(payout, tri)
        (cleared if verdict.get("verdict") == "clear" else vetoed).append(payout)

    # 3. Treasury decides funding for cleared payouts (pay_now | reject, no limbo)
    treasury_result = agents.treasury(cleared, balance, reserve_floor)
    treasury_actions = {d.get("payout_id"): d.get("action") for d in treasury_result.get("decisions", [])}
    treasury_decisions = {d.get("payout_id"): d for d in treasury_result.get("decisions", [])}

    # 3b. Reconciliation: P3 over the ledger is arithmetic, so every treasury
    # decision is checked against it in code. Mismatches become recorded
    # disputes ruled on by Resolution — code flags, agents rule.
    ledger = agents.build_ledger(cleared)
    headroom = balance - reserve_floor
    mechanical = {r["payout_id"]: ("pay_now" if r["cumulative_total"] <= headroom else "reject")
                  for r in ledger}
    ledger_rows = {r["payout_id"]: r for r in ledger}
    for pid, expected in mechanical.items():
        actual = treasury_actions.get(pid)
        if actual is not None and actual != expected:
            events.emit("reconciliation.flagged", pid, "orchestrator", {
                "treasury_action": actual,
                "ledger_expected": expected,
                "ledger_row": ledger_rows[pid],
                "headroom": headroom,
            })
            ruling = agents.reconcile(pid, ledger_rows[pid], headroom, treasury_decisions[pid])
            if ruling.get("ruling") == "enforce_ledger":
                treasury_actions[pid] = expected

    # 4. Conflict resolution: high-value vetoes get a policy review by Resolution
    for payout in vetoed:
        if payout.get("amount", 0) >= 5_000:
            veto_events = [e for e in events.explain(payout["id"]) if e["type"] == "compliance.reviewed"]
            ruling = agents.negotiate(
                payout,
                veto_events[-1]["payload"] if veto_events else {},
                {"position": "high-value client payout, requests policy review of the veto"},
            )
            final = "payout.approved" if ruling.get("ruling") == "override_with_conditions" else "payout.rejected"
        else:
            final = "payout.rejected"
        events.emit(final, payout["id"], "orchestrator", {})

    for payout in cleared:
        action = treasury_actions.get(payout["id"], "reject")
        events.emit(
            "payout.approved" if action == "pay_now" else "payout.rejected",
            payout["id"], "orchestrator",
            {} if payout["id"] in treasury_actions else {"reason": "no treasury decision — rejected by default"},
        )

    # 5. Auditor explains every finalized payout (cheap model, in parallel)
    with ThreadPoolExecutor(max_workers=8) as pool:
        audits = list(pool.map(agents.audit, [p["id"] for p in payouts]))
    explanations = {p["id"]: a for p, a in zip(payouts, audits)}

    events.emit("batch.completed", "batch", "orchestrator", {})
    anchor.anchor_now()
    return {"state": events.fold_state(), "explanations": explanations}
