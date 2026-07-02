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

TREASURY_SYS = f"""You are the Treasury agent. You decide funding order.
{PAYOUT_POLICY}
Given cleared payouts and the treasury balance, return JSON:
{{"decisions": [{{"payout_id": str, "action": "pay_now"|"reject", "reason": str}}]}}
Every payout gets a decision. "reject" ONLY if paying it would take the balance
below the reserve floor after funding lower-amount payouts first (P3)."""

NEGOTIATOR_SYS = f"""You are the Resolution agent. Compliance vetoed a payout that
Treasury wants to pay. Rule strictly on policy. Return JSON:
{{"ruling": "uphold_veto"|"override_with_conditions", "conditions": [str], "reason": str}}
{PAYOUT_POLICY}
Uphold every veto that correctly cites P1 or P2 — no exceptions, no conditions can
cure a sanctions hit. Override ONLY if the veto misapplied policy (e.g., vetoed on
P4 flags alone), and state what verification the override is conditioned on."""

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


def treasury(cleared: list[dict], balance: float, reserve_floor: float) -> dict:
    result = llm.complete(
        TREASURY_SYS,
        str({"payouts": cleared, "balance": balance, "reserve_floor": reserve_floor}),
    )
    for d in result.get("decisions", []):
        events.emit("treasury.decided", d.get("payout_id", "?"), "treasury", d)
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
