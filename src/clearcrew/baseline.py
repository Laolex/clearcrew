"""Single-agent baseline: one monolithic prompt does the whole job.

This is what the society is benchmarked against. Same model family, same task.
"""
from . import llm
from .policy import PAYOUT_POLICY

MONOLITH_SYS = f"""You are a payout-operations system. For EVERY payout in the batch,
decide approve/reject by applying the org policy below exactly.
{PAYOUT_POLICY}
Return JSON: {{"decisions": [{{"payout_id": str, "action": "approve"|"reject", "reason": str}}]}}"""


def run_batch(payouts: list[dict], balance: float = 100_000.0, reserve_floor: float = 10_000.0) -> dict:
    return llm.complete(
        MONOLITH_SYS,
        str({"payouts": payouts, "balance": balance, "reserve_floor": reserve_floor}),
    )
