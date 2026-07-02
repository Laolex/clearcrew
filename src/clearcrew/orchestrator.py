"""Society orchestrator: task decomposition, role routing, conflict resolution."""
from . import agents, events


def run_batch(payouts: list[dict], balance: float = 100_000.0, reserve_floor: float = 10_000.0) -> dict:
    events.emit("batch.received", "batch", "orchestrator", {"count": len(payouts)})

    # 1. Decompose: intake triages every request (cheap model, parallelizable)
    triaged = [(p, agents.intake(p)) for p in payouts]

    # 2. Route by risk tier: low-risk skips deep compliance review
    cleared, vetoed = [], []
    for payout, tri in triaged:
        if tri.get("risk_tier") == "low" and not tri.get("flags"):
            events.emit("compliance.fast_tracked", payout["id"], "orchestrator", {})
            cleared.append(payout)
            continue
        verdict = agents.compliance(payout, tri)
        (cleared if verdict.get("verdict") == "clear" else vetoed).append(payout)

    # 3. Treasury decides funding for cleared payouts
    treasury_result = agents.treasury(cleared, balance, reserve_floor)

    # 4. Conflict resolution: treasury may contest a veto on high-value payouts
    for payout in vetoed:
        if payout.get("amount", 0) >= 5_000:
            veto_events = [e for e in events.explain(payout["id"]) if e["type"] == "compliance.reviewed"]
            ruling = agents.negotiate(payout, veto_events[-1]["payload"] if veto_events else {}, {"position": "high-value client payout, requests override"})
            final = "payout.approved" if ruling.get("ruling") == "override_with_conditions" else "payout.rejected"
        else:
            final = "payout.rejected"
        events.emit(final, payout["id"], "orchestrator", {})

    for d in treasury_result.get("decisions", []):
        if d.get("action") == "pay_now":
            events.emit("payout.approved", d["payout_id"], "orchestrator", {})

    # 5. Auditor explains every finalized payout
    explanations = {p["id"]: agents.audit(p["id"]) for p in payouts}

    events.emit("batch.completed", "batch", "orchestrator", {})
    return {"state": events.fold_state(), "explanations": explanations}
