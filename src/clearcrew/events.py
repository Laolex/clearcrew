"""Append-only event log: the society's single source of truth.

Every agent decision, dispute, and resolution is an event. State is a fold over
events; `explain(subject_id)` reconstructs the causal chain for any payout.
"""
import json
import time
import uuid
from pathlib import Path

from . import config


def emit(event_type: str, subject: str, actor: str, payload: dict) -> dict:
    event = {
        "id": uuid.uuid4().hex[:12],
        "ts": time.time(),
        "type": event_type,
        "subject": subject,
        "actor": actor,
        "payload": payload,
    }
    with open(config.EVENT_LOG_PATH, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event


def read_all() -> list[dict]:
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
