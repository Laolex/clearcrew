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
through a single monolithic agent, and reports accuracy, token cost, latency —
and auditability, which the monolith can't offer at all.

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
