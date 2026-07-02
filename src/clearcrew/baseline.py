"""Single-agent baseline: one monolithic prompt does the whole job.

This is what the society is benchmarked against. Same model family, same task.
"""
from . import llm, policy
from .policy import PAYOUT_POLICY

MONOLITH_SYS = f"""You are a payout-operations system. For EVERY payout in the batch,
decide approve/reject by applying the org policy below exactly.
{PAYOUT_POLICY}
Return JSON: {{"decisions": [{{"payout_id": str, "action": "approve"|"reject", "reason": str}}]}}"""


def run_batch(payouts: list[dict], balance: float = policy.BALANCE, reserve_floor: float = policy.RESERVE_FLOOR) -> dict:
    return llm.complete(
        MONOLITH_SYS,
        str({"payouts": payouts, "balance": balance, "reserve_floor": reserve_floor}),
    )
