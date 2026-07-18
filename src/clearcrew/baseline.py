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


def run_batch(payouts: list[dict], balance: float | None = None,
              reserve_floor: float | None = None) -> dict:
    balance = policy.CURRENT.balance if balance is None else balance
    reserve_floor = policy.CURRENT.reserve_floor if reserve_floor is None else reserve_floor
    # The benchmark runs each system in its own subprocess, so the parent's
    # llm.usage_totals never sees these calls — the counter has to travel back
    # in the result. (It didn't, for a while, and the token numbers silently
    # became stale.)
    result = _decide(payouts, balance, reserve_floor)
    result["usage"] = dict(llm.usage_totals)
    return result


def _decide(payouts: list[dict], balance: float, reserve_floor: float) -> dict:
    return llm.complete(
        MONOLITH_SYS.replace(PAYOUT_POLICY, policy.CURRENT.render()),
        str({
            "payouts": payouts,
            "amount_ledger": build_ledger(payouts),
            "balance": balance,
            "reserve_floor": reserve_floor,
            "headroom": round(balance - reserve_floor, 2),
        }),
    )
