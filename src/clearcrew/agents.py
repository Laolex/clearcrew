"""The society's specialist roles. Each agent sees only its slice of the task."""
from . import config, events, llm
from .policy import PAYOUT_POLICY

INTAKE_SYS = f"""You are the Intake agent in a payout-operations team.
{PAYOUT_POLICY}
Given a payout request, classify it. Return JSON:
{{"risk_tier": "low"|"medium"|"high", "reason": str, "flags": [str]}}
"high" = plausibly rejectable under P1/P2. "low" = clearly none of P1/P2 apply.
Record P4 flags but remember they are not rejection grounds."""

COMPLIANCE_SYS = f"""You are the Compliance agent. You can VETO payouts.
{PAYOUT_POLICY}
Given a payout request and intake flags, return JSON:
{{"verdict": "clear"|"veto", "reason": str, "policy_rule": "P1"|"P2"|"none"}}
Veto ONLY on a concrete policy rule (P1 or P2) and cite it. Per P4, flags alone
are never veto grounds — clear those and note the flags in your reason."""

TREASURY_SYS = f"""You are the Treasury agent. You decide funding order — and ONLY
funding order. Separation of duties: every payout you receive has ALREADY passed
compliance review; you may not re-evaluate compliance rules (P1/P2) under any
circumstances. Your sole rule is P3:
{PAYOUT_POLICY}
You receive a running ledger computed deterministically by the orchestrator:
payouts sorted lowest-amount-first, each with the cumulative total if it and all
cheaper payouts are funded, plus the available headroom (balance minus reserve
floor). Do NOT redo the arithmetic — the ledger's sums are authoritative. Your
job is to APPLY P3 to it: fund in ledger order while cumulative_total <=
headroom; reject any payout whose cumulative_total exceeds headroom. Return JSON:
{{"decisions": [{{"payout_id": str, "action": "pay_now"|"reject", "reason": str}}]}}
Every payout in the ledger gets a decision."""

NEGOTIATOR_SYS = f"""You are the Resolution agent. Compliance vetoed a payout that
Treasury wants to pay. Rule strictly on policy. Return JSON:
{{"ruling": "uphold_veto"|"override_with_conditions", "conditions": [str], "reason": str}}
{PAYOUT_POLICY}
Uphold every veto that correctly cites P1 or P2 — no exceptions, no conditions can
cure a sanctions hit. Override ONLY if the veto misapplied policy (e.g., vetoed on
P4 flags alone), and state what verification the override is conditioned on."""

RECONCILE_SYS = f"""You are the Resolution agent. The orchestrator's deterministic
ledger check disagrees with Treasury's funding decision on ONE payout. P3 over a
computed ledger is arithmetic: fund in ledger order while cumulative_total <=
headroom; reject once it exceeds headroom. The ledger's sums are computed in code
and are authoritative — do not redo them.
{PAYOUT_POLICY}
Compare Treasury's stated action AND its stated reason against the ledger row.
Return JSON: {{"ruling": "uphold_treasury"|"enforce_ledger", "reason": str}}
Rule "uphold_treasury" ONLY if the ledger check itself misapplied P3."""

AUDITOR_SYS = """You are the Auditor. Given the full event chain for one payout,
write a 2-sentence plain-English explanation of what happened and why. Return JSON:
{"explanation": str}"""


def intake(payout: dict) -> dict:
    result = llm.complete(INTAKE_SYS, str(payout), model=config.MODEL_FAST, think=False)
    events.emit("intake.classified", payout["id"], "intake", result)
    return result


def compliance(payout: dict, intake_result: dict) -> dict:
    result = llm.complete(COMPLIANCE_SYS, str({"payout": payout, "intake": intake_result}))
    events.emit("compliance.reviewed", payout["id"], "compliance", result)
    return result


def build_ledger(payouts: list[dict]) -> list[dict]:
    """Deterministic running ledger: agents judge, ledgers add. Arithmetic is
    never delegated to a model — this is computed in code and handed to
    Treasury (and, for benchmark fairness, to the monolith baseline too)."""
    rows, total = [], 0.0
    for p in sorted(payouts, key=lambda p: p["amount"]):
        total += p["amount"]
        rows.append({"payout_id": p["id"], "amount": p["amount"], "cumulative_total": round(total, 2)})
    return rows


def treasury(cleared: list[dict], balance: float, reserve_floor: float) -> dict:
    result = llm.complete(
        TREASURY_SYS,
        str({
            "ledger": build_ledger(cleared),
            "balance": balance,
            "reserve_floor": reserve_floor,
            "headroom": round(balance - reserve_floor, 2),
        }),
    )
    for d in result.get("decisions", []):
        events.emit("treasury.decided", d.get("payout_id", "?"), "treasury", d)
    return result


def reconcile(payout_id: str, ledger_row: dict, headroom: float, treasury_decision: dict) -> dict:
    result = llm.complete(
        RECONCILE_SYS,
        str({"ledger_row": ledger_row, "headroom": headroom, "treasury": treasury_decision}),
    )
    events.emit("dispute.resolved", payout_id, "resolution", result)
    return result


def negotiate(payout: dict, veto: dict, treasury_position: dict) -> dict:
    result = llm.complete(
        NEGOTIATOR_SYS,
        str({"payout": payout, "compliance_veto": veto, "treasury": treasury_position}),
    )
    events.emit("dispute.resolved", payout["id"], "resolution", result)
    return result


def audit(payout_id: str) -> dict:
    chain = events.explain(payout_id)
    result = llm.complete(AUDITOR_SYS, str(chain), model=config.MODEL_FAST, think=False)
    events.emit("audit.explained", payout_id, "auditor", result)
    return result
