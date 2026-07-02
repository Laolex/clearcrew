"""The society's specialist roles. Each agent sees only its slice of the task."""
from . import config, events, llm

INTAKE_SYS = """You are the Intake agent in a payout-operations team.
Given a payout request, classify it. Return JSON:
{"risk_tier": "low"|"medium"|"high", "reason": str, "flags": [str]}
Flag anything unusual: round amounts over 5000, brand-new recipients, mismatched
country/currency, duplicate-looking requests."""

COMPLIANCE_SYS = """You are the Compliance agent. You can VETO payouts.
Given a payout request and intake flags, return JSON:
{"verdict": "clear"|"veto", "reason": str}
Veto sanctioned-country corridors, structuring patterns, or unverifiable recipients.
Be strict but not paranoid — vetoing good payouts has a cost too."""

TREASURY_SYS = """You are the Treasury agent. You decide funding and batching.
Given cleared payouts and the treasury balance, return JSON:
{"decisions": [{"payout_id": str, "action": "pay_now"|"defer", "reason": str}]}
Never let the balance go below the reserve floor."""

NEGOTIATOR_SYS = """You are the Resolution agent. Compliance vetoed a payout that
Treasury wants to pay. Read both positions and rule. Return JSON:
{"ruling": "uphold_veto"|"override_with_conditions", "conditions": [str], "reason": str}
Compliance wins ties. An override must state concrete verification conditions."""

AUDITOR_SYS = """You are the Auditor. Given the full event chain for one payout,
write a 2-sentence plain-English explanation of what happened and why. Return JSON:
{"explanation": str}"""


def intake(payout: dict) -> dict:
    result = llm.complete(INTAKE_SYS, str(payout), model=config.MODEL_FAST)
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
    result = llm.complete(AUDITOR_SYS, str(chain), model=config.MODEL_FAST)
    events.emit("audit.explained", payout_id, "auditor", result)
    return result
