# ClearCrew

**A verifiable agent society for payout operations** — built on Qwen Cloud for the
Global AI Hackathon Series (Agent Society track).

Five specialist Qwen agents — Intake, Compliance, Treasury, Resolution, Auditor —
divide a batch of payout requests through task decomposition and negotiated
conflict resolution. Every decision is an event in an append-only log: state is a
fold over events, and any outcome can be replayed and explained.

```
batch → Intake (triage, qwen-turbo)
      → Compliance (veto power, qwen-max)   ─┐ disputes → Resolution agent
      → Treasury (funding/batching)          ─┘ (structured negotiation, recorded)
      → Auditor (plain-English explanation of every payout's event chain)
```

## Why a society beats one big agent

`python -m clearcrew.bench` runs the same labeled batch through the society and
through a single monolithic agent. Both receive the identical org policy; the
labels model the full policy, including the reserve-floor funding waterfall.

| batch | system | accuracy | tokens | seconds | auditable |
|---|---|---|---|---|---|
| n=12 | society | 100% | 21,992 | 146 | ✓ |
| n=12 | monolith | 100% | 3,894 | 54 | ✗ |
| n=36 | society | **100%** | 62,374 | 399 | ✓ |
| n=36 | monolith | **89%** | 9,961 | 139 | ✗ |

At n=36 the monolith fails silently in both directions: it approves $30,000 of
payouts that breach the treasury reserve floor, and rejects two perfectly clean
$5,000 payouts with no recoverable explanation. The society gets all 36 right —
including the two rejections that require doing the funding-waterfall arithmetic
across the whole batch — and every one of its decisions has a replayable event
trail (`runs/*.jsonl`).

The trail is not just explanation — it's *repair*: an earlier run's log showed
Treasury hallucinating a compliance violation, caught in-band by the Auditor
agent; the fix (separation of duties) came straight from reading the recorded
reasoning. See `docs/demo-notes.md`.

## Run

```bash
pip install -r requirements.txt
export DASHSCOPE_API_KEY=sk-...   # Qwen Cloud / Model Studio key
cd src && python -m clearcrew.bench
```

## Stack

- **Models**: `qwen3.7-max` (reasoning roles), `qwen3.7-plus` (triage/audit) via Qwen Cloud
  DashScope OpenAI-compatible endpoint
- **Deploy**: Alibaba Cloud Function Compute (see `Dockerfile`)
- **Provenance**: append-only JSONL event log; `events.explain(id)` reconstructs any
  payout's causal chain

## License

MIT
