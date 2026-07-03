"""Settlement client: honest conversion, unambiguous mapping, loud failure."""
import pytest

from clearcrew import settlement


def test_usdc_amount_scale_recorded():
    assert settlement.usdc_amount(9_800.0) == 0.98
    assert settlement.usdc_amount(850.0) == 0.085
    assert settlement.SCALE == 10_000


def test_settle_payout_happy_path(monkeypatch):
    calls = []

    def fake_req(method, path, body=None):
        calls.append((method, path))
        if path == "/demo/batch":
            assert body == {"amounts": [0.085]}
            return {"batchId": "b1"}
        if path == "/batches/b1":
            return {"items": [{"id": "item1", "status": "SETTLED"}]}
        if path.startswith("/receipts"):
            return {"receipts": [{"id": "r1", "subjectId": "item1", "kind": "payout.settled",
                                  "contentHash": "ch", "outcome": {"txHash": "0xabc"}}]}
        raise AssertionError(path)

    monkeypatch.setattr(settlement, "_req", fake_req)
    facts = settlement.settle_payout(850.0)
    assert facts["tx_hash"] == "0xabc"
    assert facts["settled_amount_usdc"] == 0.085
    assert facts["source_amount_usd"] == 850.0
    assert "1:10000" in facts["scale"]
    assert facts["receipt_id"] == "r1"


def test_settle_payout_fails_loudly_on_rail_failure(monkeypatch):
    def fake_req(method, path, body=None):
        if path == "/demo/batch":
            return {"batchId": "b2"}
        return {"items": [{"id": "i", "status": "FAILED"}]}

    monkeypatch.setattr(settlement, "_req", fake_req)
    with pytest.raises(settlement.SettlementError):
        settlement.settle_payout(120.0)


def test_missing_key_is_explicit(monkeypatch):
    monkeypatch.delenv("VERASETTLE_API_KEY", raising=False)
    with pytest.raises(settlement.SettlementError, match="VERASETTLE_API_KEY"):
        settlement._req("GET", "/anything")
