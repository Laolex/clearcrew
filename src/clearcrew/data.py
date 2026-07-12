"""Synthetic payout batches with labeled ground truth for the benchmark."""
import random

from . import policy

CORRIDORS = [
    ("US", "PH", "USD"), ("GB", "NG", "USD"), ("DE", "KE", "USD"),
    ("US", "IR", "USD"),  # sanctioned — must be rejected
    ("US", "CO", "USD"), ("FR", "IN", "USD"),
]


# Payouts the written policy APPROVES but that look guilty — each one sits just
# on the safe side of a rule while wearing every symptom of the rule it misses.
#
# They exist because a veto is only worth arbitrating if a veto can be wrong. On
# the standard batch compliance is never wrong (every recorded veto correctly
# cites P1 or P2), so Resolution has nothing it should ever overturn and its
# ruling is unfalsifiable. These are the cases where upholding the veto is the
# error — P4 says flags "are NOT grounds for rejection on their own".
#
# Nothing here is rigged toward an override: the payouts are legal, and whether
# compliance over-vetoes them is the agent's own call. If it clears them, the
# society was right and no dispute is recorded.
HARD_CASES = [
    {
        # 1 USD under the P2 threshold. New account, no memo, round number.
        "id": "hard0p2edge",
        "amount": 8_999.0, "currency": "USD",
        "from_country": "US", "to_country": "PH",
        "recipient_age_days": 2, "memo": "",
    },
    {
        # Sanctions apply to the DESTINATION. This one is merely *from* Iran.
        "id": "hard1srcsan",
        "amount": 6_500.0, "currency": "USD",
        "from_country": "IR", "to_country": "DE",
        "recipient_age_days": 400, "memo": "consulting retainer",
    },
    {
        # Old account, so P2 cannot bite however large the amount is.
        "id": "hard2bigold",
        "amount": 15_000.0, "currency": "USD",
        "from_country": "GB", "to_country": "NG",
        "recipient_age_days": 400, "memo": "",
    },
]


def make_batch(n: int = 12, seed: int = 7, hard: bool = False) -> list[dict]:
    """`hard=True` appends HARD_CASES. It defaults off because the archived runs
    are re-derived from this function by id — changing the default batch would
    silently break the enrichment of every run already on disk."""
    rng = random.Random(seed)
    batch = []
    for i in range(n):
        src, dst, ccy = rng.choice(CORRIDORS)
        amount = rng.choice([120.0, 850.0, 2400.0, 5000.0, 9800.0, 15000.0])
        payout = {
            "id": f"{rng.getrandbits(32):08x}",
            "amount": amount,
            "currency": ccy,
            "from_country": src,
            "to_country": dst,
            "recipient_age_days": rng.choice([2, 30, 400]),
            "memo": rng.choice(["contract work", "invoice 4471", "aid disbursement", ""]),
        }
        batch.append(payout)

    if hard:
        batch.extend({**c} for c in HARD_CASES)

    # Ground truth = the executable policy itself: labels and counterfactual
    # replay share one implementation, so they can't drift apart
    verdicts = policy.evaluate(batch)
    for p in batch:
        p["_expected"] = verdicts[p["id"]]["verdict"]
    return batch
