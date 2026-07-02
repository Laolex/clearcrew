"""Replay Time Machine API: serves real archived runs, rejects bad input."""
import json

import pytest
from fastapi.testclient import TestClient

from clearcrew import replay


@pytest.fixture
def client(tmp_path, monkeypatch):
    run = tmp_path / "events-test-n12.jsonl"
    lines = [
        {"id": "e1", "ts": 1.0, "type": "batch.received", "subject": "batch",
         "actor": "orchestrator", "payload": {"count": 1}},
        {"id": "e2", "ts": 2.0, "type": "intake.classified", "subject": "aaaa1111",
         "actor": "intake", "payload": {"risk_tier": "low", "reason": "small amount"}},
        {"id": "e3", "ts": 3.0, "type": "payout.approved", "subject": "aaaa1111",
         "actor": "orchestrator", "payload": {}},
    ]
    run.write_text("\n".join(json.dumps(e) for e in lines) + "\n")
    (tmp_path / "results-test-n12.json").write_text(
        json.dumps({"society": {"accuracy": 1.0, "tokens": 1, "seconds": 1, "auditable": True},
                    "monolith": {"accuracy": 0.9, "tokens": 1, "seconds": 1, "auditable": False}}))
    monkeypatch.setattr(replay, "RUNS_DIR", tmp_path)
    return TestClient(replay.app)


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_list_runs_includes_results(client):
    runs = client.get("/api/runs").json()["runs"]
    assert len(runs) == 1
    assert runs[0]["n"] == 12
    assert runs[0]["results"]["society"]["accuracy"] == 1.0


def test_run_detail_folds_status(client):
    d = client.get("/api/runs/events-test-n12.jsonl").json()
    assert d["total_events"] == 3
    payout = next(p for p in d["payouts"] if p["id"] == "aaaa1111")
    assert payout["status"] == "approved"
    assert payout["events"] == 2


def test_explain_returns_ordered_chain_with_offsets(client):
    d = client.get("/api/runs/events-test-n12.jsonl/explain/aaaa1111").json()
    assert [e["type"] for e in d["chain"]] == ["intake.classified", "payout.approved"]
    assert d["chain"][0]["t_offset"] == 1.0  # relative to batch start


def test_unknown_run_and_subject_404(client):
    assert client.get("/api/runs/events-nope-n5.jsonl").status_code == 404
    assert client.get("/api/runs/events-test-n12.jsonl/explain/zzzz").status_code == 404


def test_path_traversal_rejected(client):
    for evil in ("..%2F..%2Fetc%2Fpasswd", "events-..-n1.jsonl%2F..%2Fx"):
        assert client.get(f"/api/runs/{evil}").status_code in (404, 422)


def test_index_serves_ui(client):
    r = client.get("/")
    assert r.status_code == 200 and "Replay Time Machine" in r.text
