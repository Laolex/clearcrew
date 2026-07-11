"""Append-only event log: the society's single source of truth.

Every agent decision, dispute, and resolution is an event. State is a fold over
events; `explain(subject_id)` reconstructs the causal chain for any payout.

Events are hash-chained: each event commits to its predecessor's hash, so the
recorded history is tamper-evident — edit or drop any event and every hash
after it breaks. `verify_chain` recomputes the chain from scratch. (Runs
recorded before hashing existed simply have no hashes; they are reported as
such, never retro-hashed — rewriting history is the one thing this system
must never do.)

## Why the store is a database and the archive is a file

The chain is sound only if exactly one writer at a time reads the tip, links to
it, and appends. The first version of this file guarded that with a
`threading.Lock`, which is per-process — and this system has always run more
than one process on the log (the MCP server and a batch run are two). Two
writers each read the same tip and each chained onto it. The result was not
corruption but a **fork**: every event present, both branches internally
hash-valid, and a linear walk misreporting it as tampering. Anchor that and you
attest to one branch while the other sits in the log looking legitimate.

An advisory `flock` prevents that only so long as every writer agrees to take
it. So the tip constraint is enforced by the *store* instead:

    prev_hash TEXT NOT NULL UNIQUE

Two events cannot claim the same predecessor, because the second INSERT violates
a UNIQUE index. A fork is not detected after the fact — it is **impossible**, and
the loser of the race retries against the new tip. `BEGIN IMMEDIATE` serialises
writers so the race is rare; the UNIQUE index is the airtight backstop for when
it isn't. (This mirrors `@civ/history`'s `UNIQUE(world_id, parent_hash)`.)

The same table buys the other two things a JSONL file could not:

- **Indexed reads.** `explain()` was a full parse of the log to find one payout's
  events. It is now an index lookup on `subject`, and `fold_state()` aggregates
  in SQL — neither is O(total history) any more.
- **Idempotency.** An `emit()` retried after a timeout used to record the event
  twice. Pass `idempotency_key` and the retry is a no-op that returns the
  original event.

JSONL remains the **archive and evidence format** — `export_jsonl()` writes it,
byte-compatible with every run already in `runs/`. The database is the writer;
the file is what you hand to an auditor.
"""
import hashlib
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from . import config, schema

GENESIS = "0" * 64

_lock = threading.Lock()
_MAX_RETRIES = 8

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  seq        INTEGER PRIMARY KEY AUTOINCREMENT,
  id         TEXT NOT NULL UNIQUE,
  subject    TEXT NOT NULL,
  type       TEXT NOT NULL,
  prev_hash  TEXT NOT NULL UNIQUE,
  event_hash TEXT NOT NULL UNIQUE,
  doc        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_subject ON events(subject);
"""

# The event as recorded, verbatim, lives in `doc`. The columns beside it exist to
# query and to constrain — never to re-assemble the event, because a column list
# silently drops any field it does not know about (`schema_version` was the first
# casualty). `doc` is what is hashed, what is exported, and what an auditor reads.
_FIELDS = ("id", "ts", "type", "subject", "actor", "payload", "prev_hash", "event_hash")


def _db_path(path: str | None = None) -> str:
    p = path or config.EVENT_LOG_PATH
    return p[:-6] + ".db" if p.endswith(".jsonl") else p + ".db"


_initialised: set[str] = set()


def _connect(path: str | None = None) -> sqlite3.Connection:
    db = _db_path(path)
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    # Check before connecting — connect() creates the file, so an existence test
    # afterwards is always true and would skip DDL on a log that was archived away.
    fresh = db not in _initialised or not Path(db).exists()
    # isolation_level=None: we drive transactions explicitly with BEGIN IMMEDIATE
    conn = sqlite3.connect(db, timeout=30.0, isolation_level=None)
    conn.execute("PRAGMA synchronous=FULL")  # durability: survive power loss
    if fresh:
        # Switching journal mode and creating the schema both need a brief exclusive
        # lock, so two processes starting at once will race for it and one gets
        # "database is locked". Both are idempotent and the winner's work persists in
        # the file, so the loser just waits and re-checks rather than dying.
        for attempt in range(_MAX_RETRIES):
            try:
                conn.execute("PRAGMA journal_mode=WAL")  # persisted in the file
                conn.executescript(_SCHEMA)
                break
            except sqlite3.OperationalError:
                time.sleep(0.05 * (attempt + 1))
        else:
            raise RuntimeError(f"event log: could not initialise {db}")
        _initialised.add(db)
    return conn


def _event_hash(event: dict) -> str:
    material = {k: event[k] for k in ("id", "ts", "type", "subject", "actor", "payload", "prev_hash")}
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _row_to_event(row: sqlite3.Row) -> dict:
    return json.loads(row["doc"])


def _rollback(conn: sqlite3.Connection) -> None:
    """Abandon the transaction, if one is open.

    `BEGIN IMMEDIATE` can itself fail on a busy lock, in which case no
    transaction exists and a bare ROLLBACK raises *inside* the error handler —
    killing the writer and losing every event it had left to append. A writer
    that dies silently is the failure this whole store exists to prevent.
    """
    try:
        conn.execute("ROLLBACK")
    except sqlite3.OperationalError:
        pass  # no transaction was open


def emit(event_type: str, subject: str, actor: str, payload: dict,
         idempotency_key: str | None = None) -> dict:
    """Append one event, linked to the current tip.

    `idempotency_key` makes the append safe to retry: a second emit with the same
    key returns the event already recorded instead of writing a duplicate.
    """
    with _lock:  # intra-process; the UNIQUE index is what makes it safe across processes
        conn = _connect()
        conn.row_factory = sqlite3.Row
        try:
            for attempt in range(_MAX_RETRIES):
                try:
                    conn.execute("BEGIN IMMEDIATE")

                    if idempotency_key:
                        prior = conn.execute(
                            "SELECT doc FROM events WHERE id = ?", (idempotency_key,)).fetchone()
                        if prior:
                            _rollback(conn)
                            return _row_to_event(prior)

                    tip = conn.execute(
                        "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
                    event = {
                        "id": idempotency_key or uuid.uuid4().hex[:12],
                        "ts": time.time(),
                        "type": event_type,
                        "subject": subject,
                        "actor": actor,
                        "payload": payload,
                        "prev_hash": tip["event_hash"] if tip else GENESIS,
                    }
                    event = schema.validate(event)
                    event["event_hash"] = _event_hash(event)

                    conn.execute(
                        "INSERT INTO events (id, subject, type, prev_hash, event_hash, doc)"
                        " VALUES (?,?,?,?,?,?)",
                        (event["id"], event["subject"], event["type"], event["prev_hash"],
                         event["event_hash"], json.dumps(event)),
                    )
                    conn.execute("COMMIT")
                    return event

                except sqlite3.IntegrityError:
                    # Another writer took this tip first. There is no fork to clean up —
                    # the UNIQUE index refused it. Re-read the new tip and chain onto that.
                    _rollback(conn)
                    continue
                except sqlite3.OperationalError:
                    # Busy lock. Back off and re-read the tip.
                    _rollback(conn)
                    time.sleep(0.01 * (attempt + 1))
                    continue
            raise RuntimeError("event log: could not append after retries")
        finally:
            conn.close()


def reset_chain(path: str | None = None) -> None:
    """No-op, kept for callers that archive a log mid-run.

    The tip is read from the store inside the append transaction, so there is no
    cached hash left to invalidate — which is the point: the cache was the bug.
    """


def tail_hash(path: str | None = None) -> str:
    """Hash of the log's head — what an anchor commits to."""
    conn = _connect(path)
    try:
        tip = conn.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        return tip[0] if tip else GENESIS
    finally:
        conn.close()


def verify_chain(events: list[dict]) -> dict:
    """Recompute the hash chain.

    Returns {'hashed', 'verified', 'events', 'broken_at', 'forks', 'orphans'}.

    `broken_at` is the first index that fails a linear walk. `forks` and
    `orphans` say *why*, and they are not the same failure:

    - **fork**: two events claim the same `prev_hash`, each self-consistent.
      Two writers raced. History was not edited — it was branched.
    - **orphan**: an event's `prev_hash` names no event in the log. Something
      upstream was dropped.
    - neither, but `verified` is False: the content no longer matches its own
      hash. That is tampering.

    The live store makes forks impossible; this still checks for them, because
    it also runs over archived JSONL written by older, forkable versions.
    """
    if not events:
        return {"hashed": False, "verified": False, "events": 0,
                "broken_at": None, "forks": [], "orphans": []}
    if "event_hash" not in events[0]:
        return {"hashed": False, "verified": False, "events": len(events),
                "broken_at": None, "forks": [], "orphans": []}

    seen: dict[str, int] = {}
    for e in events:
        seen[e.get("prev_hash")] = seen.get(e.get("prev_hash"), 0) + 1
    forks = [h for h, n in seen.items() if n > 1]
    hashes = {e.get("event_hash") for e in events}
    orphans = [e.get("id") for e in events
               if e.get("prev_hash") != GENESIS and e.get("prev_hash") not in hashes]

    prev = GENESIS
    broken_at = None
    for i, e in enumerate(events):
        if e.get("prev_hash") != prev or _event_hash(e) != e.get("event_hash"):
            broken_at = i
            break
        prev = e["event_hash"]

    return {
        "hashed": True,
        "verified": broken_at is None and not forks and not orphans,
        "events": len(events),
        "broken_at": broken_at,
        "forks": forks,
        "orphans": orphans,
    }


def read_all(path: str | None = None) -> list[dict]:
    conn = _connect(path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM events ORDER BY seq ASC").fetchall()
        return [_row_to_event(r) for r in rows]
    finally:
        conn.close()


def explain(subject: str) -> list[dict]:
    """Causal chain for one payout: every event that touched it, in order.

    Indexed on `subject` — this reads the events for one payout, not the log.
    """
    conn = _connect()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM events WHERE subject = ? ORDER BY seq ASC", (subject,)).fetchall()
        return [_row_to_event(r) for r in rows]
    finally:
        conn.close()


_TERMINAL = ("payout.approved", "payout.rejected", "payout.settled")


def fold_state() -> dict:
    """Current status of every payout, derived purely from the log.

    Folded in SQL: the status is the last terminal event per subject, and the
    history count is an aggregate. Neither replays the whole log in Python.
    """
    conn = _connect()
    try:
        state = {s: {"status": "unknown", "history": n} for s, n in conn.execute(
            "SELECT subject, COUNT(*) FROM events GROUP BY subject")}
        rows = conn.execute(
            f"SELECT subject, type FROM events WHERE type IN ({','.join('?' * len(_TERMINAL))})"
            " ORDER BY seq ASC", _TERMINAL)
        for subject, etype in rows:
            state[subject]["status"] = etype.split(".", 1)[1]
        return state
    finally:
        conn.close()


def export_jsonl(dest: str, src: str | None = None) -> int:
    """Write the log out as JSONL — the archive and evidence format.

    Byte-compatible with every run already in `runs/`: same fields, same order,
    emission order preserved. The database is the writer; this is what an auditor
    reads, and what `replay` and the console load.
    """
    events = read_all(src)
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")  # verbatim: never a field subset
    return len(events)


def load_jsonl(path: str) -> list[dict]:
    """Read an archived JSONL log. Tolerates a torn trailing line (an append that
    never committed), but never reads past corruption anywhere else."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[dict] = []
    lines = [ln for ln in p.read_text().splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            if i == len(lines) - 1:
                break
            raise
    return out
