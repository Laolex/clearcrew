# Threat Model

What can go wrong when agents move money, and which mechanism in this repo
answers it. Mitigations name real code; the last section lists what we do
**not** claim to mitigate.

## Threats and mitigations

| Threat | Mitigation | Mechanism |
|---|---|---|
| **Double payment** | One single-item settlement batch per approved payout — unambiguous decision→settlement mapping — with per-item idempotency on the rail side | `settlement.py` |
| **Tampered history** (edited reason, amount, verdict) | sha256 hash chain over canonical JSON; `verify_chain()` recomputes end-to-end and reports the exact break index. **The chain alone only stops an attacker who cannot rewrite the file** — see below. Against one who can, the defence is the external anchor: an RFC-3161 token from an independent authority binding the head hash to a signed timestamp | `events.py`, `anchor.py` |
| **Rogue/mistaken agent approval** (incl. prompt injection via payout fields) | **Prevention, not just detection**: agents *propose*; the deterministic policy layer promotes. An approval the policy forbids (P1/P2/P3) cannot be recorded — the attempt is written as `policy.blocked` and the payout is rejected. The gate is veto-only: it can refuse an approval, never manufacture one | `orchestrator.py` `_promote()`, `policy.py` |
| **Lost reasoning** ("why did the agent do that?") | Verbatim model reasons recorded in every judgment event, plus a plain-language `audit.explained` narrative per payout | `events.py`, auditor agent |
| **Settlement ambiguity** (did money actually move?) | Receipt required back from the rail: `settlement.confirmed` carries the on-chain `tx_hash`, checkable on any Base Sepolia RPC — no receipt, no `payout.settled` | `settlement.py` |
| **Staged demo data** | The demo replays the same hash-chained logs shipped in `runs/`; the chain verifies live in the UI; judge mode runs the society + real testnet settlement on demand | `replay.py`, judge mode |
| **Replay that secretly recomputes** | The replay surface is a read-only fold over the event log — no model calls exist in that code path, so replayed history cannot drift from recorded history | `replay.py` |
| **Unauthorized live runs** (cost/abuse) | Judge mode requires an access code and enforces a daily run cap; everything else is read-only | `replay.py` `/api/live/*` |
| **Malformed events entering the record** | Schema validation inside `emit()`, before hashing — an event that doesn't parse can't join the chain | `schema.py` |

## The honest row: what the hash chain does and does not prove

The hash chain is computed by the same process that writes the log. So on its
own it proves **integrity against accident and against a naive edit** — change
one byte and `verify_chain()` names the exact broken index — but *not* integrity
against an adversary with write access, who can edit event 12, recompute every
hash after it, and produce a chain that verifies clean. Hash chaining alone is
tamper-**evident**, not tamper-**proof**, and any project claiming otherwise is
overselling a sha256 loop.

Closing that gap needs one thing the writer cannot reach: a copy of the head
hash held elsewhere. That is what `anchor.py` does — an RFC-3161 Time Stamping
Authority signs `(our head hash, its clock)` with its own key, and we record the
token. Rewriting history now requires forging a third party's signature.

Its limits, stated rather than buried:

- **Only the anchored prefix is protected.** Events written after the most
  recent anchor are as rewritable as before; the tamper window is the anchor
  interval. We anchor at the end of every batch.
- **We do not verify the TSA's signature ourselves** — deliberately. We check
  that the token is granted and commits to our hash; verifying the authority's
  own signature is left to `openssl ts -verify`, so nobody has to trust our code
  for the part that matters.
- **It proves the log wasn't edited, not that it was ever true.** An anchor
  cannot tell you the agents were honest — only that nobody rewrote what they
  said.

## Prevention vs detection, after the gate

This project used to say the policy layer "grades, it does not gate," and that
was true. It is no longer the whole truth.

Agents now **propose**; the deterministic policy layer **promotes**. An approval
that P1/P2/P3 forbid cannot become a terminal decision — the attempt is recorded
as `policy.blocked` and the payout is rejected. The reserve floor is therefore an
**invariant**, not a benchmark result: no run can record an approval that
breaches it, whatever Treasury believed.

Two things stay honestly scoped:

- **The gate is veto-only.** It can refuse an approval; it can never create one.
  The policy layer models arithmetic (P1–P3), not judgment, disputes, or the P4
  flags the agents exist to weigh. A gate that could approve would be deciding
  rather than constraining, and the society would be decorative.
- **Agents can still be wrong in the direction the gate doesn't cover** — they
  can propose to reject something that should have been paid. Policy will not
  overrule that, and it shouldn't. Those misses remain detected and attributed,
  not prevented.

So the claim is now two claims: *bad approvals cannot be recorded*, and *when
agents are wrong in any other way, the record shows exactly who, when, and
against which rule.*

## Explicitly out of scope (v1)

- **Key custody / production wallets** — settlement runs on a testnet sandbox;
  no mainnet keys, no custody claims.
- **Durable storage** — the event store is append-only JSONL, ideal for
  auditability and replay, not yet replicated or backed by a database.
- **Denial of service / rate limiting** beyond the judge-mode daily cap.
- **Model supply chain** — Qwen models are consumed as a cloud service; we
  record what they said, not what they were.
- **Adversarial recipients** (mule accounts, synthetic identity) — policy `P1`/`P2`
  encode simple compliance rules, not a fraud stack.

Each of these is a roadmap item, not an accident — see
[GUARANTEES.md](GUARANTEES.md) for the implemented/roadmap split.
