"""Append-only event log: the society's single source of truth.

Every agent decision, dispute, and resolution is an event. State is a fold over
events; `explain(subject_id)` reconstructs the causal chain for any payout.

Events are hash-chained: each event commits to its predecessor's hash, so the
recorded history is tamper-evident — edit or drop any event and every hash
after it breaks. `verify_chain` recomputes the chain from scratch. (Runs
recorded before hashing existed simply have no hashes; they are reported as
such, never retro-hashed — rewriting history is the one thing this system
must never do.)

Thread safety: a single lock serializes all reads AND writes so concurrent
readers never see a partial line. Writes append directly to the log file
(not a temp-file rename), which is safe because POSIX write(2) on a local
filesystem is page-atomic for sub-page writes; the lock ensures Python-level
exclusion so no reader interleaves between JSON serialization and the write.
"""
import hashlib
import json
import threading
import time
import uuid
from pathlib import Path

from . import config, schema

GENESIS = "0" * 64

_lock = threading.Lock()
_last_hash: dict[str, str] = {}  # log path -> hash of its last event


def _event_hash(event: dict) -> str:
    material = {k: event[k] for k in ("id", "ts", "type", "subject", "actor", "payload", "prev_hash")}
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _tail_hash(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return GENESIS
    last = None
    with open(p) as f:
        for line in f:
            if line.strip():
                last = line
    if last is None:
        return GENESIS
    return json.loads(last).get("event_hash", GENESIS)


def emit(event_type: str, subject: str, actor: str, payload: dict) -> dict:
    with _lock:
        path = config.EVENT_LOG_PATH
        if path not in _last_hash:
            _last_hash[path] = _tail_hash(path)
        event = {
            "id": uuid.uuid4().hex[:12],
            "ts": time.time(),
            "type": event_type,
            "subject": subject,
            "actor": actor,
            "payload": payload,
            "prev_hash": _last_hash[path],
        }
        event = schema.validate(event)
        event["event_hash"] = _event_hash(event)
        with open(path, "a") as f:
            f.write(json.dumps(event) + "\n")
            f.flush()
        _last_hash[path] = event["event_hash"]
        return event


def reset_chain(path: str | None = None) -> None:
    """Forget the cached tail hash (e.g. after archiving a log file)."""
    _last_hash.pop(path or config.EVENT_LOG_PATH, None)


def verify_chain(events: list[dict]) -> dict:
    """Recompute the hash chain. Returns {'hashed', 'verified', 'events', 'broken_at'}."""
    if not events:
        return {"hashed": False, "verified": False, "events": 0, "broken_at": None}
    if "event_hash" not in events[0]:
        return {"hashed": False, "verified": False, "events": len(events), "broken_at": None}
    prev = GENESIS
    for i, e in enumerate(events):
        if e.get("prev_hash") != prev or _event_hash(e) != e.get("event_hash"):
            return {"hashed": True, "verified": False, "events": len(events), "broken_at": i}
        prev = e["event_hash"]
    return {"hashed": True, "verified": True, "events": len(events), "broken_at": None}


def read_all() -> list[dict]:
    with _lock:
        path = Path(config.EVENT_LOG_PATH)
        if not path.exists():
            return []
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]


def explain(subject: str) -> list[dict]:
    """Causal chain for one payout: every event that touched it, in order."""
    return [e for e in read_all() if e["subject"] == subject]


def fold_state() -> dict:
    """Current status of every payout, derived purely from the log."""
    state: dict[str, dict] = {}
    for e in read_all():
        s = state.setdefault(e["subject"], {"status": "unknown", "history": 0})
        s["history"] += 1
        if e["type"] in ("payout.approved", "payout.rejected", "payout.settled"):
            s["status"] = e["type"].split(".", 1)[1]
    return state
