"""Ground-truth labels must model the FULL policy — this is what round three
of the benchmark taught us (labels that skip the waterfall punish correct
treasury behavior)."""
from clearcrew import data, policy


def test_batch_is_deterministic():
    a, b = data.make_batch(36), data.make_batch(36)
    assert a == b
    assert len({p["id"] for p in a}) == 36


def test_p1_sanctioned_destinations_rejected():
    for p in data.make_batch(64):
        if p["to_country"] == "IR":
            assert p["_expected"] == "reject"


def test_p2_large_payouts_to_new_accounts_rejected():
    for p in data.make_batch(64):
        if p["amount"] >= 9000 and p["recipient_age_days"] <= 7:
            assert p["_expected"] == "reject"


def test_p3_approved_total_never_breaches_reserve_floor():
    for n in (12, 36, 64):
        approved = sum(p["amount"] for p in data.make_batch(n) if p["_expected"] == "approve")
        assert approved <= policy.BALANCE - policy.RESERVE_FLOOR


def test_p3_waterfall_is_lowest_amount_first():
    batch = data.make_batch(36)
    clean_rejects = [
        p["amount"] for p in batch
        if p["_expected"] == "reject"
        and p["to_country"] != "IR"
        and not (p["amount"] >= 9000 and p["recipient_age_days"] <= 7)
    ]
    approved = [p["amount"] for p in batch if p["_expected"] == "approve"]
    # anything rejected purely for the floor must be >= every approved payout
    if clean_rejects and approved:
        assert min(clean_rejects) >= max(approved)


def test_build_ledger_is_sorted_cumulative():
    from clearcrew.agents import build_ledger
    rows = build_ledger([{"id": "b", "amount": 300.0}, {"id": "a", "amount": 100.0}, {"id": "c", "amount": 200.0}])
    assert [r["payout_id"] for r in rows] == ["a", "c", "b"]
    assert [r["cumulative_total"] for r in rows] == [100.0, 300.0, 600.0]
