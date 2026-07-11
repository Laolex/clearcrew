# Threat Model

What can go wrong when agents move money, and which mechanism in this repo
answers it. Mitigations name real code; the last section lists what we do
**not** claim to mitigate.

## Threats and mitigations

| Threat | Mitigation | Mechanism |
|---|---|---|
| **Double payment** | One single-item settlement batch per approved payout — unambiguous decision→settlement mapping — with per-item idempotency on the rail side | `settlement.py` |
| **Tampered history** (edited reason, amount, verdict) | sha256 hash chain over canonical JSON; `verify_chain()` recomputes end-to-end and reports the exact break index; verification state is displayed, never asserted | `events.py` |
| **Lost reasoning** ("why did the agent do that?") | Verbatim model reasons recorded in every judgment event, plus a plain-language `audit.explained` narrative per payout | `events.py`, auditor agent |
| **Rogue/mistaken agent approval** (incl. prompt injection via payout fields) | Layered, honestly scoped: the deterministic policy layer (`P1`–`P3`) provides ground truth; every terminal decision is **graded against it and misses are flagged on the record** (the UI's `?? miss` glyph and Failures page). Detection and attribution, not hard prevention — see below | `policy.py`, benchmark, Failures view |
| **Settlement ambiguity** (did money actually move?) | Receipt required back from the rail: `settlement.confirmed` carries the on-chain `tx_hash`, checkable on any Base Sepolia RPC — no receipt, no `payout.settled` | `settlement.py` |
| **Staged demo data** | The demo replays the same hash-chained logs shipped in `runs/`; the chain verifies live in the UI; judge mode runs the society + real testnet settlement on demand | `replay.py`, judge mode |
| **Replay that secretly recomputes** | The replay surface is a read-only fold over the event log — no model calls exist in that code path, so replayed history cannot drift from recorded history | `replay.py` |
| **Unauthorized live runs** (cost/abuse) | Judge mode requires an access code and enforces a daily run cap; everything else is read-only | `replay.py` `/api/live/*` |
| **Malformed events entering the record** | Schema validation inside `emit()`, before hashing — an event that doesn't parse can't join the chain | `schema.py` |

## The honest row: prevention vs detection

The mechanical policy layer is a **grader, not a gate**: agents can and do
miss (that's what the benchmark measures, and misses are first-class recorded
outcomes — red-flagged in the UI, attributed to an actor and a rule). The
claim is not "agents can't be wrong"; it's "**when they're wrong, the record
shows exactly who, when, and against which rule** — and the money trail shows
whether it mattered." For payouts, that's the property auditors actually buy.

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
