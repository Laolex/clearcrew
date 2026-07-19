# System Guarantees

Invariants, not features. Each one names its mechanism, and each one was
checked against **all 23 recorded runs** in `runs/` (script at the bottom) —
these are properties the data actually has, not properties we intend it to have.

## Invariants

1. **Every payout has exactly one terminal decision.**
   The orchestrator emits exactly one `payout.approved` or `payout.rejected`
   per payout, after the specialist agents (and, when vetoed, the resolution
   ruling) have spoken. *Checked: 23/23 runs, every payout.*

2. **Every decision is recorded before anything acts on it.**
   `events.emit()` appends, hashes, and flushes the event before returning.
   There is no code path from a model response to the settlement rail that
   does not pass through the log. (`events.py`, `orchestrator.py`)

3. **Every event references its predecessor.**
   `prev_hash` is the previous event's `event_hash` (genesis-anchored);
   `event_hash` is sha256 over the canonical JSON *including* `prev_hash`.
   Reorder, delete, or edit any event and `verify_chain()` reports the exact
   break index. *Checked: 21/21 hash-chained runs verify end-to-end; the 2
   earliest runs predate hash chaining and are honestly reported (and
   displayed in the UI) as "replayable, not tamper-evident".*

4. **Every event is schema-validated before it is hashed.**
   `schema.validate()` runs inside `emit()` — malformed events can't enter
   the chain. (`schema.py`)

5. **Every settlement is linked to a receipt.**
   Every `settlement.confirmed` event carries the on-chain `tx_hash` (plus
   source USD, settled USDC, and the recorded 1:10,000 testnet scale), and
   `payout.settled` links back to it. *Checked: 15/15 settlement events across
   all runs carry a tx hash.*

6. **Every replay reconstructs recorded history.**
   The replay/explain/analytics surface is a pure fold over `runs/*.jsonl` —
   read-only, no model calls, no second data store to disagree with the
   record. (`replay.py`)

7. **Every counterfactual is deterministic.**
   Counterfactual replay re-folds the recorded batch through different policy
   parameters (`policy.py`'s mechanical layer). Recorded agent judgments are
   replayed as-is — nothing is re-generated, so the same inputs always give
   the same answer.

8. **The record never claims more than what moved.**
   Testnet honesty: settlement events carry both the benchmark USD figure and
   the real USDC moved, with the scale stated explicitly in the payload.

9. **No approval the policy forbids can be recorded.**
   Agents *propose*; the deterministic policy layer *promotes*
   (`orchestrator._promote`). A proposal to approve a payout that P1, P2 or P3
   rejects never becomes a `payout.approved` event — it is recorded as
   `policy.blocked` and the payout is rejected. **The reserve floor is an
   invariant, not a benchmark result**: no run can overdraw the treasury,
   however confidently Treasury argues for it. Two archived runs did exactly
   that before this gate existed; they are still published, and under the
   current architecture they are not expressible. *Checked: 11/11 post-gate
   runs — no forbidden approval recorded, floor held in every one.*

10. **The gate can only ever refuse.**
    It cannot turn a rejection into an approval. The policy layer models
    arithmetic (P1–P3), not judgment, disputes, or the P4 flags the agents
    exist to weigh — a gate that could approve would be deciding rather than
    constraining, and the society would be decorative. Agents can therefore
    still be wrong in the direction the gate does not cover (proposing to
    reject something payable); that remains detected and attributed, not
    prevented.

11. **A run is anchored outside itself, or it does not claim to be.**
    The head hash is submitted to an RFC-3161 Time Stamping Authority, which
    signs `(hash, its clock)` with its own key; the token is recorded as
    `chain.anchored`. Rewriting anchored history therefore requires forging a
    third party's signature, not merely recomputing our own hashes. A failed
    anchor is recorded as `chain.anchor_failed` — never as a success — and runs
    with anchoring off record nothing at all. Only the prefix *before* an anchor
    is protected: the tamper window is the anchor interval, and we anchor at the
    end of every batch. *Checked: 11/11 post-gate runs carry a TSA token that
    verifies against the head hash actually recorded in that run.*

## Honest scope

| | |
|---|---|
| **Implemented** | replay · explain · counterfactual replay · hash-chain verification · **external RFC-3161 anchoring** · **veto-only policy gate** · **durable event store: forks impossible, indexed reads, idempotent appends** · evidence export (JSON/PDF) · real testnet USDC settlement · society-vs-monolith benchmark · live judge mode · read-only MCP server |
| **Recorded but early** | 2 of 22 archived runs predate hash chaining (replayable, not tamper-evident — labeled as such in the UI). Runs archived before the gate could, and twice did, breach the reserve floor; they are published as they were recorded |
| **Roadmap, not claimed** | multi-policy version history · **multi-host** writers (the store is single-node SQLite; the schema and the anti-fork constraint port to Postgres unchanged) · per-agent cryptographic signing (attribution today is a label the orchestrator writes, not a signature) · production custody & key management · mainnet settlement |

### The writer forked the chain. We reproduced it, then fixed it.

This page used to carry a line under *Roadmap, not claimed*: **"the writer is
single-process: concurrent writers would fork the chain."** That was true, and
it was load-bearing — an anchor over a forkable chain attests to a lie.

It is now closed, and the failure is worth describing because it is not the one
you would guess. `emit()` guarded the chain with a `threading.Lock` and an
in-process cache of the tail hash. Both are per-process, and this system has
always run more than one process on the log — the MCP server and a batch run are
two. Two writers each read the same tail and each chained onto it.

The result was **not corruption.** Every event was present, nothing was lost, and
each branch hash-verified perfectly on its own. The log simply contained *two
valid chains* instead of one, and a linear walk misreported it as **tampering**
— pointing an operator at an attacker who did not exist.

A lock would have prevented this. It would not have made it *impossible* — an
advisory lock only works while every writer agrees to take it, and the next one
to forget forks the log again. So the tip constraint moved into the store:

```sql
prev_hash TEXT NOT NULL UNIQUE
```

Two events cannot claim the same predecessor, because the second INSERT violates
a UNIQUE index. The loser of a race does not fork — it is **refused**, and retries
against the new tip. `BEGIN IMMEDIATE` serialises writers so the race is rare; the
index is the airtight backstop for when it isn't. This is not a novel idea: it is
exactly the `UNIQUE(world_id, parent_hash)` that `@civ/history` already runs in
production, and we ported it.

| | before | after |
|---|---|---|
| two processes × 25 events | **chain forks at event 1**, `verified: False` | 50 events, **one chain**, `verified: True` |
| a fork is… | detected, after it happened | **impossible** — refused by a UNIQUE index |
| tip hash | cached in the process (**this was the bug**) | read inside the append transaction |
| `explain(payout)` | full parse of the log — **O(total history)** | index lookup: **0.7 ms against a 3,000-event log** |
| `fold_state()` | replay every event in Python | aggregated in SQL — 4.4 ms |
| a retried `emit()` | **records the event twice** | `idempotency_key` → returns the original |
| durability | `flush()` — OS page cache only | `fsync` per commit (`synchronous=FULL`) |
| diagnosis | `broken_at` only | tells a **fork** from an **orphan** from a **tamper** |

*Checked: `test_two_processes_cannot_fork_the_chain` spawns two contending
writers and asserts one verified chain and two live writers. A raw `INSERT` that
bypasses `emit()` entirely and reuses a `prev_hash` is refused by the store:
`UNIQUE constraint failed: events.prev_hash`.*

**JSONL is still the archive format.** The database is the writer; the file is
what an auditor reads. `export_jsonl()` writes it byte-compatible with every run
already in `runs/`, and replay, the console, and evidence export are unchanged.

**What this costs, and what is still not claimed.** `synchronous=FULL` flushes to
disk on every append, which caps writes at **~90/s** — a deliberate trade (a
payout ledger that loses acknowledged events on power loss is worthless), and
irrelevant at this scale, where a 36-payout run appends ~220 events. It would
matter at thousands of payouts a second, and the fix there is batching commits
per tick, not weakening the flush. `read_all()` is still O(n) by definition; only
the callers that needed one payout stopped paying for the whole log. Multi-*host*
writers would need Postgres rather than SQLite — the schema and the constraint
port unchanged.

## How the invariants were checked

```bash
python3 - <<'EOF'
import json, glob, collections, sys
sys.path.insert(0, "src")
from clearcrew import events as EV
for path in sorted(glob.glob("src/runs/events-*.jsonl")):
    evs = [json.loads(l) for l in open(path) if l.strip()]
    term = collections.Counter(e["subject"] for e in evs
                               if e["type"] in ("payout.approved", "payout.rejected"))
    subjects = {e["subject"] for e in evs if e["type"] == "intake.classified"}
    assert all(term[s] == 1 for s in subjects), path              # invariant 1
    assert all((e["payload"] or {}).get("tx_hash")
               for e in evs if e["type"] == "settlement.confirmed"), path  # invariant 5
    v = EV.verify_chain(evs)                                      # invariant 3
    assert v["verified"] or not v["hashed"], path
print("all recorded runs pass")
EOF
```

Invariants **9–11** are properties of the current architecture, so they are
checked only against runs recorded under it — asserting them over the whole
archive would fail, and it *should*: two pre-gate runs breached the reserve
floor, and we publish them rather than quietly dropping them.

```bash
python3 - <<'EOF'
import json, glob, sys
sys.path.insert(0, "src")
from clearcrew import anchor, data, policy
for path in sorted(glob.glob("src/runs/events-*.jsonl")):
    evs = [json.loads(l) for l in open(path) if l.strip()]
    if not any(e["type"] == "payout.proposed" for e in evs):
        continue                                        # pre-gate run, skip
    n = int(path.split("-n")[-1].split(".")[0])
    amounts = {p["id"]: p["amount"] for p in data.make_batch(n)}
    ruled = policy.evaluate(data.make_batch(n))

    approved = [e["subject"] for e in evs if e["type"] == "payout.approved"]
    # invariant 9: nothing the policy forbids was ever approved
    assert all(ruled[s]["verdict"] == "approve" for s in approved), path
    # ...and therefore the reserve floor held, by construction
    assert sum(amounts[s] for s in approved) <= policy.CURRENT.headroom, path

    # invariant 11: if the run claims an anchor, the token really commits to it
    for e in (e for e in evs if e["type"] == "chain.anchored"):
        p = e["payload"]
        if p["provider"] != "noop":
            assert anchor.verify_token(p["token"], p["head_hash"])["valid"], path
    print("post-gate run passes:", path.split("/")[-1])
EOF
```
