"""Event schema validation: typed payloads catch drift at write time."""
import pytest

from clearcrew import events, schema


def test_known_event_type_is_validated(tmp_path, monkeypatch):
    monkeypatch.setattr("clearcrew.config.EVENT_LOG_PATH", str(tmp_path / "log.jsonl"))
    events.reset_chain()
    e = events.emit("intake.classified", "p1", "intake",
                    {"risk_tier": "low", "reason": "small amount", "flags": []})
    assert e["schema_version"] == 1
    assert e["payload"]["risk_tier"] == "low"


def test_unknown_event_type_passes_through(tmp_path, monkeypatch):
    monkeypatch.setattr("clearcrew.config.EVENT_LOG_PATH", str(tmp_path / "log.jsonl"))
    events.reset_chain()
    e = events.emit("custom.type", "p1", "test", {"anything": 42})
    assert e["schema_version"] == 1
    assert e["payload"]["anything"] == 42


def test_invalid_payload_does_not_block_event(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("clearcrew.config.EVENT_LOG_PATH", str(tmp_path / "log.jsonl"))
    events.reset_chain()
    e = events.emit("intake.classified", "p1", "intake",
                    {"risk_tier": "nope", "reason": "bad"})
    assert e is not None
    assert "schema validation skipped" in caplog.text


def test_schema_dataclass_roundtrip():
    from clearcrew.schema import IntakeClassified
    obj = IntakeClassified(risk_tier="high", reason="sanctions", flags=["P1"])
    d = obj.__dataclass_fields__
    assert set(d) == {"risk_tier", "reason", "flags"}
