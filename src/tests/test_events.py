"""Event log invariants: append-only, replayable, state = fold(events)."""
import json
import multiprocessing as mp
import os

import clearcrew.config as config
from clearcrew import events


def _concurrent_writer(path: str, actor: str, n: int, barrier) -> None:
    """A second service writing to the same log — e.g. the MCP server while a
    batch runs. Must be module-level to survive `spawn`."""
    os.environ["CLEARCREW_EVENT_LOG"] = path
    from clearcrew import config as c
    from clearcrew import events as e
    c.EVENT_LOG_PATH = path
    barrier.wait()  # pay the import cost first, then contend for real
    for i in range(n):
        e.emit("intake.classified", f"{actor}-{i}", actor,
               {"risk_tier": "low", "reason": "t", "flags": []})


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
    assert v == {"hashed": True, "verified": True, "events": 5, "broken_at": None,
                 "forks": [], "orphans": []}


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


def test_two_processes_cannot_fork_the_chain(tmp_path):
    """The chain must survive two writers in two PROCESSES.

    A `threading.Lock` and a cached tail hash are both per-process, so two
    services on one log each read the same tail and each append to it. The
    result is not corruption: every event is present and each branch verifies
    internally. It is a *fork* — and anchoring it attests to one branch while
    the other sits in the log looking legitimate.
    """
    path = str(tmp_path / "chain.jsonl")
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(2)
    procs = [ctx.Process(target=_concurrent_writer, args=(path, actor, 25, barrier))
             for actor in ("svc-a", "svc-b")]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)

    # A writer that dies on a busy lock loses every event it had left to append,
    # and the chain still verifies — the loss is invisible. Check it survived.
    assert [p.exitcode for p in procs] == [0, 0], "a writer died mid-append"

    log = events.read_all(path)

    assert len(log) == 50, "no event may be lost to a racing writer"
    v = events.verify_chain(log)
    assert v["forks"] == [], "two writers chained onto the same predecessor"
    assert v["orphans"] == []
    assert v["verified"] is True, f"one log, one chain: {v}"


def test_a_retried_emit_does_not_record_the_event_twice(tmp_path, monkeypatch):
    """An emit that times out and is retried must not append two events.

    Without an idempotency key the log would carry the same decision twice, and
    every fold over it would double-count.
    """
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "chain.jsonl"))
    first = events.emit("payout.approved", "p1", "orchestrator", {}, idempotency_key="settle-p1")
    again = events.emit("payout.approved", "p1", "orchestrator", {}, idempotency_key="settle-p1")

    assert again == first, "the retry must return the original event, not a new one"
    assert len(events.read_all()) == 1
    assert events.verify_chain(events.read_all())["verified"] is True


def test_export_jsonl_roundtrips_the_chain(tmp_path, monkeypatch):
    """JSONL is the archive format: what an auditor reads must verify exactly."""
    monkeypatch.setattr(config, "EVENT_LOG_PATH", str(tmp_path / "chain.jsonl"))
    for i in range(5):
        events.emit("intake.classified", f"p{i}", "intake",
                    {"risk_tier": "low", "reason": "r", "flags": []})
    dest = tmp_path / "archived.jsonl"
    assert events.export_jsonl(str(dest)) == 5

    exported = events.load_jsonl(str(dest))
    assert exported == events.read_all()
    assert events.verify_chain(exported)["verified"] is True
