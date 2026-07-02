"""Event log invariants: append-only, replayable, state = fold(events)."""
import clearcrew.config as config
from clearcrew import events


def test_emit_read_explain_fold_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))

    events.emit("intake.classified", "abc123", "intake", {"risk_tier": "low"})
    events.emit("payout.approved", "abc123", "orchestrator", {})
    events.emit("intake.classified", "def456", "intake", {"risk_tier": "high"})
    events.emit("payout.rejected", "def456", "orchestrator", {"reason": "P1"})

    all_events = events.read_all()
    assert len(all_events) == 4
    assert all(set(e) >= {"id", "ts", "type", "subject", "actor", "payload"} for e in all_events)

    chain = events.explain("abc123")
    assert [e["type"] for e in chain] == ["intake.classified", "payout.approved"]

    state = events.fold_state()
    assert state["abc123"]["status"] == "approved"
    assert state["def456"]["status"] == "rejected"
    assert state["def456"]["history"] == 2


def test_empty_log_folds_to_empty_state(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "missing.jsonl"))
    assert events.read_all() == []
    assert events.fold_state() == {}


def test_hash_chain_emit_and_verify(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "chain.jsonl"))
    events.reset_chain(config.EVENT_LOG_PATH)
    for i in range(5):
        events.emit("intake.classified", f"p{i}", "intake", {"i": i})
    log = events.read_all()
    assert log[0]["prev_hash"] == events.GENESIS
    assert all(log[i]["prev_hash"] == log[i - 1]["event_hash"] for i in range(1, 5))
    v = events.verify_chain(log)
    assert v == {"hashed": True, "verified": True, "events": 5, "broken_at": None}


def test_tampering_breaks_the_chain(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "chain.jsonl"))
    events.reset_chain(config.EVENT_LOG_PATH)
    for i in range(4):
        events.emit("treasury.decided", f"p{i}", "treasury", {"action": "pay_now"})
    log = events.read_all()

    edited = [dict(e) for e in log]
    edited[1]["payload"] = {"action": "reject"}  # rewrite one decision
    assert events.verify_chain(edited)["verified"] is False
    assert events.verify_chain(edited)["broken_at"] == 1

    dropped = log[:1] + log[2:]  # delete an event
    assert events.verify_chain(dropped)["verified"] is False


def test_prehash_runs_report_unhashed():
    legacy = [{"id": "x", "ts": 1.0, "type": "t", "subject": "s", "actor": "a", "payload": {}}]
    v = events.verify_chain(legacy)
    assert v["hashed"] is False and v["verified"] is False
