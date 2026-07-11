# Design Principles

Five rules decided the architecture. Each one is a constraint we chose to accept,
and each one costs us something — the cost is named.

## 1. Replay over recomputation

**State is a fold over recorded events, never a re-run of a model.**

`replay.py` reconstructs any past moment by folding the event log. It does not
call an LLM. This is why "replay" means the same thing here as it does in a
database and not the same thing it means in most agent demos, where "replay"
quietly re-invokes the model and hopes it says the same thing twice.

*Cost:* every fact the UI shows must have been written to the log at the time it
happened. Nothing can be reconstructed after the fact by asking the model again.

## 2. History over prompts

**The log is the source of truth; the prompt is a derived artifact.**

Agents read from the recorded history, and what they emit goes back into it —
verbatim, including their stated reasons. We never keep a decision in memory,
act on it, and record it afterwards: `events.emit()` flushes *before* the
orchestrator acts on the verdict.

*Cost:* a write on the hot path of every decision. Worth it — the alternative is
a system whose record can disagree with what it did.

## 3. Proof over explanation

**A hash chain, not a well-written summary.**

Anyone can generate a persuasive account of what an agent did. `verify_chain()`
recomputes every `event_hash` from `prev_hash` and the canonical JSON body, and
on tampering reports the **exact index** where the chain breaks. That is a
mechanism, not a promise.

*Cost:* events are immutable. There is no edit, no backfill, no "fixing" a bad
record — a correction is a new event that references the old one.

## 4. Execution after governance

**Only `payout.approved` can reach the money rail.**

`settlement.py` takes a verdict, not a suggestion. There is no path from an agent
to a transfer that does not pass through a recorded terminal decision. This is
the invariant that makes the demo safe to run against real testnet USDC.

*Cost:* the system cannot act fast on an obviously-fine payout without first
producing the record. We think that's the point.

## 5. Evidence over screenshots

**Every claim we make is one `GET` away from being checked.**

`/explain/{payout}` returns the decision, the chain, the receipt, and the
verification result — the same JSON in [`evidence-pack-example.json`](evidence-pack-example.json).
Nothing in this repo asks you to trust a screenshot, a video, or us.

*Cost:* we can't hide a weak run. All ten recorded runs are in the log, including
the two that predate hash chaining and the ones where the society made mistakes.

---

## Why this isn't another agent framework

Frameworks give you orchestration. The gap they leave is what happens *after*
the agents finish talking — and on a payout desk, that gap is the whole job.

| | a typical agent framework | ClearCrew |
|---|---|---|
| **What it is** | a library for wiring agents together | an accountable system of record that happens to use agents |
| **Source of truth** | conversation history in memory | append-only hash-chained event log |
| **"Replay"** | re-invoke the model, hope for the same output | fold recorded events — **no model is ever re-run** |
| **Tamper evidence** | none | `verify_chain()` names the exact broken index |
| **Reasons** | in the trace, if you enabled tracing | first-class recorded events, verbatim, attributed to an actor |
| **Counterfactual** | re-prompt and compare | re-fold the same batch against a changed policy — **deterministic** |
| **Policy** | prose in a system prompt | executable code (`policy.py`) that both grades and replays |
| **Money** | a tool call the agent may make | a rail only a recorded `payout.approved` can reach |
| **Evidence** | logs you have to interpret | an export a counterparty can verify without us |
| **Failure mode** | silent, unattributable | recorded, attributed, and — in our own runs — caught by the Auditor |

The honest version of the distinction: **a framework helps agents act. This helps
you prove what they did, and stops them acting until they have.** If you don't
need the second thing, you don't need this — use a framework and go faster.

We do need it. The whole reason the payout desk still has humans in it is that
somebody has to be able to answer "why did this money move?" a year later, to
someone who was not in the room and does not trust anyone who was.

See also: [ARCHITECTURE](ARCHITECTURE.md) · [TRUST_MODEL](TRUST_MODEL.md) · [GUARANTEES](GUARANTEES.md) · [BENCHMARK](BENCHMARK.md)
