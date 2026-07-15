"""API auth: endpoints require Bearer token when CLEARCREW_API_TOKEN is set."""
import json

import pytest
from fastapi.testclient import TestClient

from clearcrew import replay


@pytest.fixture(autouse=True)
def reset_token():
    yield
    replay.API_TOKEN = ""


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "RUNS_DIR", tmp_path)
    replay.API_TOKEN = ""
    run = tmp_path / "events-test-n12.jsonl"
    lines = [
        {"id": "e1", "ts": 1.0, "type": "batch.received", "subject": "batch",
         "actor": "orchestrator", "payload": {"count": 1}},
        {"id": "e2", "ts": 2.0, "type": "payout.approved", "subject": "aaaa1111",
         "actor": "orchestrator", "payload": {}},
    ]
    run.write_text("\n".join(json.dumps(e) for e in lines) + "\n")
    return TestClient(replay.app)


def test_no_auth_when_token_unset(client, monkeypatch):
    monkeypatch.delenv("CLEARCREW_API_TOKEN", raising=False)
    replay.API_TOKEN = ""
    r = client.get("/api/runs")
    assert r.status_code == 200


def test_auth_required_when_token_set(client, monkeypatch):
    monkeypatch.setenv("CLEARCREW_API_TOKEN", "s3cr3t")
    replay.API_TOKEN = "s3cr3t"
    # no token
    r = client.get("/api/runs")
    assert r.status_code == 401
    # wrong token
    r = client.get("/api/runs", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_auth_succeeds_with_valid_token(client, monkeypatch):
    monkeypatch.setenv("CLEARCREW_API_TOKEN", "s3cr3t")
    replay.API_TOKEN = "s3cr3t"
    r = client.get("/api/runs", headers={"Authorization": "Bearer s3cr3t"})
    assert r.status_code == 200


def test_event_verification_endpoint_accepts_valid_auth(client, monkeypatch):
    """The browser evidence view uses this endpoint with the shared auth header."""
    monkeypatch.setenv("CLEARCREW_API_TOKEN", "s3cr3t")
    replay.API_TOKEN = "s3cr3t"
    r = client.get("/api/runs/events-test-n12.jsonl/events",
                   headers={"Authorization": "Bearer s3cr3t"})
    assert r.status_code == 200


def test_healthz_is_unauthenticated(client, monkeypatch):
    monkeypatch.setenv("CLEARCREW_API_TOKEN", "s3cr3t")
    replay.API_TOKEN = "s3cr3t"
    r = client.get("/healthz")
    assert r.status_code == 200
