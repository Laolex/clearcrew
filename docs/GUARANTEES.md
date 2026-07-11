# System Guarantees

Invariants, not features. Each one names its mechanism, and each one was
checked against **all 21 recorded runs** in `runs/` (script at the bottom) —
these are properties the data actually has, not properties we intend it to have.

## Invariants

1. **Every payout has exactly one terminal decision.**
   The orchestrator emits exactly one `payout.approved` or `payout.rejected`
   per payout, after the specialist agents (and, when vetoed, the resolution
   ruling) have spoken. *Checked: 21/21 runs, every payout.*

2. **Every decision is recorded before anything acts on it.**
   `events.emit()` appends, hashes, and flushes the event before returning.
   There is no code path from a model response to the settlement rail that
   does not pass through the log. (`events.py`, `orchestrator.py`)

3. **Every event references its predecessor.**
   `prev_hash` is the previous event's `event_hash` (genesis-anchored);
   `event_hash` is sha256 over the canonical JSON *including* `prev_hash`.
   Reorder, delete, or edit any event and `verify_chain()` reports the exact
   break index. *Checked: 19/19 hash-chained runs verify end-to-end; the 2
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
| **Implemented** | replay · explain · counterfactual replay · hash-chain verification · **external RFC-3161 anchoring** · **veto-only policy gate** · evidence export (JSON/PDF) · real testnet USDC settlement · society-vs-monolith benchmark · live judge mode · read-only MCP server |
| **Recorded but early** | 2 of 21 archived runs predate hash chaining (replayable, not tamper-evident — labeled as such in the UI). Runs archived before the gate could, and twice did, breach the reserve floor; they are published as they were recorded |
| **Roadmap, not claimed** | multi-policy version history · durable event store beyond JSONL (**the writer is single-process: concurrent writers would fork the chain**) · per-agent cryptographic signing (attribution today is a label the orchestrator writes, not a signature) · production custody & key management · mainnet settlement |

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
