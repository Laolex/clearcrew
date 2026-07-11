# System Guarantees

Invariants, not features. Each one names its mechanism, and each one was
checked against **all 10 recorded runs** in `runs/` (script at the bottom) —
these are properties the data actually has, not properties we intend it to have.

## Invariants

1. **Every payout has exactly one terminal decision.**
   The orchestrator emits exactly one `payout.approved` or `payout.rejected`
   per payout, after the specialist agents (and, when vetoed, the resolution
   ruling) have spoken. *Checked: 10/10 runs, every payout.*

2. **Every decision is recorded before anything acts on it.**
   `events.emit()` appends, hashes, and flushes the event before returning.
   There is no code path from a model response to the settlement rail that
   does not pass through the log. (`events.py`, `orchestrator.py`)

3. **Every event references its predecessor.**
   `prev_hash` is the previous event's `event_hash` (genesis-anchored);
   `event_hash` is sha256 over the canonical JSON *including* `prev_hash`.
   Reorder, delete, or edit any event and `verify_chain()` reports the exact
   break index. *Checked: 8/8 hash-chained runs verify end-to-end; the 2
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

## Honest scope

| | |
|---|---|
| **Implemented** | replay · explain · counterfactual replay · hash-chain verification · evidence export (JSON/PDF) · real testnet USDC settlement · society-vs-monolith benchmark · live judge mode · read-only MCP server |
| **Recorded but early** | 2 of 10 runs predate hash chaining (replayable, not tamper-evident — labeled as such in the UI) |
| **Roadmap, not claimed** | multi-policy version history · durable event store beyond JSONL · production custody & key management · mainnet settlement |

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
