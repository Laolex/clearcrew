"""Single-agent baseline: one monolithic prompt does the whole job.

This is what the society is benchmarked against. Same model family, same task.
"""
from . import llm, policy
from .agents import build_ledger
from .policy import PAYOUT_POLICY

MONOLITH_SYS = f"""You are a payout-operations system. For EVERY payout in the batch,
decide approve/reject by applying the org policy below exactly.
{PAYOUT_POLICY}
The amount_ledger gives deterministic cumulative sums over ALL payouts sorted
lowest-amount-first (computed in code — trust its arithmetic). Note it includes
payouts you may reject on other grounds; account for that when applying the
reserve-floor rule.
Return JSON: {{"decisions": [{{"payout_id": str, "action": "approve"|"reject", "reason": str}}]}}"""


def run_batch(payouts: list[dict], balance: float = policy.BALANCE, reserve_floor: float = policy.RESERVE_FLOOR) -> dict:
    return llm.complete(
        MONOLITH_SYS,
        str({
            "payouts": payouts,
            "amount_ledger": build_ledger(payouts),
            "balance": balance,
            "reserve_floor": reserve_floor,
            "headroom": round(balance - reserve_floor, 2),
        }),
    )
