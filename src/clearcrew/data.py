"""Synthetic payout batches with labeled ground truth for the benchmark."""
import random
import uuid

CORRIDORS = [
    ("US", "PH", "USD"), ("GB", "NG", "USD"), ("DE", "KE", "USD"),
    ("US", "IR", "USD"),  # sanctioned — must be rejected
    ("US", "CO", "USD"), ("FR", "IN", "USD"),
]


def make_batch(n: int = 12, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    batch = []
    for i in range(n):
        src, dst, ccy = rng.choice(CORRIDORS)
        amount = rng.choice([120.0, 850.0, 2400.0, 5000.0, 9800.0, 15000.0])
        payout = {
            "id": uuid.uuid4().hex[:8],
            "amount": amount,
            "currency": ccy,
            "from_country": src,
            "to_country": dst,
            "recipient_age_days": rng.choice([2, 30, 400]),
            "memo": rng.choice(["contract work", "invoice 4471", "aid disbursement", ""]),
        }
        # ground truth label for scoring
        payout["_expected"] = "reject" if dst == "IR" or (amount >= 9800 and payout["recipient_age_days"] <= 2) else "approve"
        batch.append(payout)
    return batch
