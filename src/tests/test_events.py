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
