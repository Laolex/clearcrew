"""Synthetic payout batches with labeled ground truth for the benchmark."""
import random

from . import policy

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
            "id": f"{rng.getrandbits(32):08x}",
            "amount": amount,
            "currency": ccy,
            "from_country": src,
            "to_country": dst,
            "recipient_age_days": rng.choice([2, 30, 400]),
            "memo": rng.choice(["contract work", "invoice 4471", "aid disbursement", ""]),
        }
        # P1/P2 ground truth (mirrors PAYOUT_POLICY)
        payout["_p1p2_reject"] = dst == "IR" or (amount >= 9000 and payout["recipient_age_days"] <= 7)
        batch.append(payout)

    # P3 ground truth: fund policy-clean payouts lowest-amount-first until the
    # reserve floor binds; the rest are correct rejections
    available = policy.BALANCE - policy.RESERVE_FLOOR
    spent = 0.0
    for p in sorted((p for p in batch if not p["_p1p2_reject"]), key=lambda p: p["amount"]):
        if spent + p["amount"] <= available:
            spent += p["amount"]
            p["_expected"] = "approve"
        else:
            p["_expected"] = "reject"
    for p in batch:
        if p["_p1p2_reject"]:
            p["_expected"] = "reject"
        del p["_p1p2_reject"]
    return batch
