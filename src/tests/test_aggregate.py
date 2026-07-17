"""Cross-run aggregation helper + overview/failures/analytics/policies endpoints."""
import json

import pytest
from fastapi.testclient import TestClient

from clearcrew import replay


@pytest.fixture(autouse=True)
def _reset_token():
    replay.API_TOKEN = ""
    yield
    replay.API_TOKEN = ""


def _write_run(dirpath, stamp, n, events, results=None):
    (dirpath / f"events-{stamp}-n{n}.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n")
    if results is not None:
        (dirpath / f"results-{stamp}-n{n}.json").write_text(json.dumps(results))


@pytest.fixture
def client(tmp_path, monkeypatch):
    # one payout approved+settled, one vetoed (P2) then rejected, in a 6-payout batch
    b = replay.data.make_batch(6)
    # b[0] expects approve (settle it → correct); b[4] expects reject (veto it → correct)
    approved_id, vetoed_id = b[0]["id"], b[4]["id"]
    events = [
        {"id": "e0", "ts": 1.0, "type": "batch.received", "subject": "batch",
         "actor": "orchestrator", "payload": {"count": 6}},
        {"id": "e1", "ts": 2.0, "type": "intake.classified", "subject": approved_id,
         "actor": "intake", "payload": {"risk_tier": "low", "reason": "clean"}},
        {"id": "e2", "ts": 3.0, "type": "treasury.decided", "subject": approved_id,
         "actor": "treasury", "payload": {"action": "pay_now", "reason": "within headroom"}},
        {"id": "e3", "ts": 4.0, "type": "payout.approved", "subject": approved_id,
         "actor": "orchestrator", "payload": {}},
        {"id": "e4", "ts": 5.0, "type": "settlement.confirmed", "subject": approved_id,
         "actor": "verasettle", "payload": {"settled_amount_usdc": 0.085, "tx_hash": "0xabc",
                                            "explorer": "https://x/0xabc", "chain": "BASE-SEPOLIA",
                                            "source_amount_usd": 850.0}},
        {"id": "e5", "ts": 6.0, "type": "payout.settled", "subject": approved_id,
         "actor": "orchestrator", "payload": {"tx_hash": "0xabc", "chain": "BASE-SEPOLIA"}},
        {"id": "e6", "ts": 3.5, "type": "compliance.reviewed", "subject": vetoed_id,
         "actor": "compliance", "payload": {"verdict": "veto", "reason": "P2 hit", "policy_rule": "P2"}},
        {"id": "e7", "ts": 4.5, "type": "dispute.resolved", "subject": vetoed_id,
         "actor": "resolution", "payload": {"ruling": "uphold_veto", "reason": "correctly cites P2"}},
        {"id": "e8", "ts": 5.5, "type": "payout.rejected", "subject": vetoed_id,
         "actor": "orchestrator", "payload": {}},
    ]
    results = {"society": {"accuracy": 1.0, "tokens": 1000, "seconds": 300, "auditable": True},
               "monolith": {"accuracy": 0.8, "tokens": 500, "seconds": 150, "auditable": False}}
    _write_run(tmp_path, "test", 6, events, results)
    monkeypatch.setattr(replay, "RUNS_DIR", tmp_path)
    replay._chain_cache.clear()
    return TestClient(replay.app)


def test_scan_collects_payouts_settlements_and_failures(client, monkeypatch, tmp_path):
    monkeypatch.setattr(replay, "RUNS_DIR", tmp_path)
    scan = replay._scan_all_runs()
    assert len(scan["runs"]) == 1
    assert len(scan["payouts"]) == 2
    assert len(scan["settlements"]) == 1
    assert scan["settlements"][0]["usdc"] == 0.085
    assert len(scan["vetoes"]) == 1 and scan["vetoes"][0]["rule"] == "P2"
    assert len(scan["disputes"]) == 1 and scan["disputes"][0]["ruling"] == "uphold_veto"
    settled = [p for p in scan["payouts"] if p["settled"]]
    assert len(settled) == 1 and settled[0]["usdc"] == 0.085


def test_analytics_averages_benchmarks_and_capabilities(client):
    a = client.get("/api/analytics").json()
    assert a["society"]["accuracy"] == 1.0
    assert a["monolith"]["accuracy"] == 0.8
    assert a["settlement"]["count"] == 1
    assert a["settlement"]["usdc_moved"] == 0.085
    caps = {c["name"]: c for c in a["capabilities"]}
    assert caps["Can explain failures?"]["society"] is True
    assert caps["Can explain failures?"]["monolith"] is False
    assert a["coverage"]["replay_pct"] == 100.0


def test_society_exposes_configured_qwen_roles_and_controls(client):
    s = client.get("/api/society").json()
    assert s["provider"] == "Qwen Cloud (DashScope)"
    assert len(s["models"]) == 2
    assert all(model["name"] and model["purpose"] for model in s["models"])
    assert [r["name"] for r in s["roles"]] == [
        "Intake", "Compliance", "Treasury", "Resolution", "Auditor",
    ]
    assert len(s["controls"]) == 3


def test_overview_totals_and_recent(client):
    o = client.get("/api/overview").json()
    assert o["totals"]["runs"] == 1
    assert o["totals"]["payouts"] == 2
    assert o["totals"]["settlements"] == 1
    assert o["totals"]["usdc_moved"] == 0.085
    assert o["totals"]["replay_pct"] == 100.0
    assert len(o["recent"]) == 2
    # most-recent first by last_ts (approved payout's last event ts=6.0)
    assert o["recent"][0]["settled"] is True


def test_failures_categories_and_by_rule(client):
    f = client.get("/api/failures").json()
    cats = {c["key"]: c for c in f["categories"]}
    assert cats["compliance_vetoes"]["count"] == 1
    assert cats["compliance_vetoes"]["items"][0]["reason"] == "P2 hit"
    assert cats["disputes_resolved"]["count"] == 1
    assert cats["settlement_failures"]["count"] == 0  # honestly zero
    assert cats["benchmark_misses"]["count"] == 0     # society was 100% here
    by_rule = {r["rule"]: r["count"] for r in f["by_rule"]}
    assert by_rule["P2"] == 1


def test_policies_returns_rendered_v1(client):
    p = client.get("/api/policies").json()
    assert p["current"] == "v1"
    assert len(p["versions"]) == 1
    v = p["versions"][0]
    assert v["version"] == "v1"
    assert "P1." in v["rendered"] and "P4." in v["rendered"]
    assert v["params"]["p2_amount"] == 9000.0
    assert "one" in p["note"].lower()  # honest single-version note
