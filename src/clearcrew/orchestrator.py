"""Society orchestrator: task decomposition, role routing, conflict resolution."""
from concurrent.futures import ThreadPoolExecutor

from . import agents, events


def run_batch(payouts: list[dict], balance: float = 100_000.0, reserve_floor: float = 10_000.0) -> dict:
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
    return {"state": events.fold_state(), "explanations": explanations}
