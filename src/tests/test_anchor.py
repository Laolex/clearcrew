"""External anchoring: noop mode is the default and records the intent."""
from clearcrew import anchor, config


def test_noop_anchor_records_chain_anchored_event(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "log.jsonl"))
    monkeypatch.setenv("CLEARCREW_ANCHOR", "noop")
    from clearcrew import events
    events.reset_chain()
    events.emit("batch.received", "batch", "orchestrator", {"count": 1})
    out = anchor.anchor_now()
    assert out["type"] == "chain.anchored"
    assert out["actor"] == "anchor"
    assert out["payload"]["provider"] == "noop"
    assert len(out["payload"]["head_hash"]) == 64


def test_anchor_without_events_still_works(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "empty.jsonl"))
    monkeypatch.setenv("CLEARCREW_ANCHOR", "noop")
    from clearcrew import events
    events.reset_chain()
    out = anchor.anchor_now()
    assert out["type"] == "chain.anchored"
    assert out["payload"]["head_hash"] == events.GENESIS
