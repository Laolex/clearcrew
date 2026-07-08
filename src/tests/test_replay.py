"""Replay Time Machine API: serves real archived runs, rejects bad input."""
import json

import pytest
from fastapi.testclient import TestClient

from clearcrew import replay


@pytest.fixture(autouse=True)
def _reset_token():
    """Ensure auth is off so these tests don't get 401."""
    import clearcrew.replay as r
    r.API_TOKEN = ""
    yield


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


def test_live_disabled_without_judge_code(client, monkeypatch):
    monkeypatch.delenv("CLEARCREW_JUDGE_CODE", raising=False)
    assert client.post("/api/live/start?code=x").status_code == 503


def test_live_rejects_wrong_code(client, monkeypatch):
    monkeypatch.setenv("CLEARCREW_JUDGE_CODE", "secret")
    assert client.post("/api/live/start?code=nope").status_code == 401


def test_live_status_idle(client):
    replay._live.update(proc=None, run=None)
    assert client.get("/api/live/status").json() == {"state": "idle"}


def test_live_start_spawns_and_respects_lock(client, monkeypatch):
    monkeypatch.setenv("CLEARCREW_JUDGE_CODE", "secret")
    monkeypatch.setattr(replay, "_runs_today", lambda: 0)

    class FakeProc:
        returncode = None
        def poll(self): return None
        def kill(self): pass

    spawned = []
    monkeypatch.setattr(replay.subprocess, "Popen", lambda *a, **k: spawned.append(a) or FakeProc())
    replay._live.update(proc=None, run=None)
    assert client.post("/api/live/start?code=secret").status_code == 200
    assert len(spawned) == 1 and "clearcrew.settle_demo" in spawned[0][0]
    # second start while running -> 409
    assert client.post("/api/live/start?code=secret").status_code == 409
    replay._live.update(proc=None, run=None)


def test_settled_run_settled_is_not_a_miss():
    # against the real archived run: settled == correctly approved, never a miss
    detail = replay.run_detail("events-20260703-165045-settled-n6.jsonl")
    settled = [p for p in detail["payouts"] if p["status"] == "settled"]
    assert len(settled) == 3
    assert all(p["miss"] is False for p in settled)
    assert detail["chain"]["verified"] and detail["chain"]["events"] == 41
