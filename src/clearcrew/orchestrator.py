"""Society orchestrator: task decomposition, role routing, conflict resolution.

Agents PROPOSE; the policy gate PROMOTES. Nothing an agent says becomes a
terminal decision until the deterministic policy layer has had a chance to
refuse it — and the gate may only ever refuse. See `_promote`.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from . import agents, anchor, events, llm, policy


def run_batch(payouts: list[dict], balance: float | None = None,
              reserve_floor: float | None = None) -> dict:
    balance = policy.CURRENT.balance if balance is None else balance
    reserve_floor = policy.CURRENT.reserve_floor if reserve_floor is None else reserve_floor
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

    # 4. Conflict resolution: high-value vetoes get a policy review by Resolution.
    #    Nothing here is terminal — every branch yields a PROPOSAL.
    #
    #    Resolution can only arbitrate a disagreement that exists. Treasury never
    #    sees a payout compliance vetoed (step 3 runs over `cleared` only), so it
    #    states its funding position on the contested ones here, on its own ledger
    #    — a separate call, so the P3 waterfall over `cleared` is not contaminated
    #    by payouts compliance has already refused. Compliance objects on legality,
    #    Treasury answers on affordability, and Resolution rules between two
    #    positions that were actually taken.
    contested = [p for p in vetoed if p.get("amount", 0) >= 5_000]
    positions: dict[str, dict] = {}
    if contested:
        contested_result = agents.treasury(contested, balance, reserve_floor)
        positions = {d.get("payout_id"): d for d in contested_result.get("decisions", [])}

    proposals: dict[str, dict] = {}
    for payout in vetoed:
        pid = payout["id"]
        if payout.get("amount", 0) >= 5_000:
            veto_events = [e for e in events.explain(pid) if e["type"] == "compliance.reviewed"]
            # An absent position is recorded as absent. It is never invented: a
            # fabricated counter-argument would make the dispute a piece of
            # theatre, and the whole point of the log is that it is not.
            position = positions.get(pid) or {
                "action": "no_position",
                "reason": "Treasury recorded no funding position on this payout.",
            }
            ruling = agents.negotiate(
                payout,
                veto_events[-1]["payload"] if veto_events else {},
                position,
            )
            verdict = "approve" if ruling.get("ruling") == "override_with_conditions" else "reject"
            proposals[pid] = {"verdict": verdict, "proposed_by": "resolution"}
        else:
            proposals[pid] = {"verdict": "reject", "proposed_by": "compliance"}

    for payout in cleared:
        pid = payout["id"]
        if pid not in treasury_actions:
            proposals[pid] = {"verdict": "reject", "proposed_by": "orchestrator",
                              "reason": "no treasury decision — rejected by default"}
        else:
            proposals[pid] = {
                "verdict": "approve" if treasury_actions[pid] == "pay_now" else "reject",
                "proposed_by": "treasury",
            }

    # 5. Promotion through the policy gate — the only path to a terminal decision
    _promote(payouts, proposals, balance, reserve_floor)

    # 6. Auditor explains every finalized payout (cheap model, in parallel)
    with ThreadPoolExecutor(max_workers=8) as pool:
        audits = list(pool.map(agents.audit, [p["id"] for p in payouts]))
    explanations = {p["id"]: a for p, a in zip(payouts, audits)}

    events.emit("batch.completed", "batch", "orchestrator", {})
    anchor.anchor_now()
    return {"state": events.fold_state(), "explanations": explanations,
            "proposals": {pid: p["verdict"] for pid, p in proposals.items()},
            # the benchmark runs us in a subprocess: the parent's counter never
            # sees these calls, so the usage has to ride home in the result
            "usage": dict(llm.usage_totals)}


def _promote(payouts: list[dict], proposals: dict[str, dict],
             balance: float, reserve_floor: float) -> None:
    """The policy gate. Agents propose; this decides what may be recorded.

    Two properties, and the second is the one that matters:

    1. A proposal to APPROVE is refused if the deterministic policy says the
       payout is rejectable (P1 sanctions, P2 threshold, P3 reserve floor).
       The refusal is recorded as `policy.blocked` — the agent's intent stays
       on the record, it just never becomes executable. This is what makes the
       reserve floor an invariant instead of a grade: no run can record an
       approval that breaches it, no matter what Treasury believed.

    2. The gate is VETO-ONLY. It can never turn a rejection into an approval.
       If it could, it would be deciding rather than constraining, and the
       agents would be decorative — the policy layer models arithmetic (P1-P3),
       not judgment, disputes, or the P4 flags that agents exist to weigh.

    The proposal is emitted either way, so the benchmark still measures what the
    society actually judged. Grading terminal outcomes after a gate would score
    the gate, not the agents, and would read 100% by construction.
    """
    pv = replace(policy.CURRENT, balance=balance, reserve_floor=reserve_floor)
    ruled = policy.evaluate(payouts, pv)   # P3 only binds over the whole batch

    for payout in payouts:
        pid = payout["id"]
        proposal = proposals.get(pid, {"verdict": "reject", "proposed_by": "orchestrator",
                                       "reason": "no proposal — rejected by default"})
        verdict = proposal["verdict"]
        events.emit("payout.proposed", pid, proposal["proposed_by"],
                    {k: v for k, v in proposal.items() if k != "proposed_by"})

        blocked = None
        if verdict == "approve" and ruled[pid]["verdict"] == "reject":
            blocked = ruled[pid]["rule"]
            events.emit("policy.blocked", pid, "policy", {
                "proposed": "approve",
                "rule": blocked,
                "proposed_by": proposal["proposed_by"],
                "reason": f"policy {blocked} forbids approving this payout; "
                          f"the proposal is recorded but cannot be executed",
            })

        final = "payout.approved" if verdict == "approve" and not blocked else "payout.rejected"
        payload = {}
        if blocked:
            payload = {"reason": f"blocked by policy {blocked}", "blocked_rule": blocked}
        elif "reason" in proposal:
            payload = {"reason": proposal["reason"]}
        events.emit(final, pid, "orchestrator", payload)
