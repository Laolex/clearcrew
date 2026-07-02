# ClearCrew — Qwen Cloud Hackathon Entry Plan (Agent Society track)

**Deadline: Jul 9, 2026 @ 2:00pm PDT** (~7 days from Jul 2)

## The pitch
A verifiable agent society for payout operations. Five specialist agents (Intake,
Compliance, Treasury, Reconciler, Auditor) divide a batch of payout requests via
task decomposition and negotiated conflict resolution — every decision lands in an
append-only event log, so any outcome can be replayed and explained (`explain <id>`).
A benchmark harness runs the same batch through a single monolithic agent and
reports measurable efficiency gains (accuracy, throughput, token cost).

Why this wins the track brief:
- **Task decomposition & role assignment** — orchestrator splits batches by risk tier and routes to roles.
- **Conflict resolution** — Compliance can veto Treasury; disputes go to a structured negotiation round, resolution recorded as events.
- **Measurable efficiency vs single agent** — `bench.py` produces the comparison table for the demo video.
- Differentiator vs other entries: the event-sourced audit trail + replayable explanations (nobody else will have provenance).

## Hard requirements (from Devpost rules — all mandatory)
- [ ] Qwen models served from **Qwen Cloud** (Model Studio / DashScope international endpoint)
- [ ] Backend **deployed on Alibaba Cloud** (Function Compute or 1 small ECS) with code-level proof of Alibaba API usage
- [ ] **Public open-source repo** with a detectable license (MIT) — fresh code only; NO Civ0 or Verasettle core code (Civ0 is mid–Zero Cup tournament, Verasettle is proprietary)
- [ ] Architecture diagram
- [ ] ~3-minute demo video
- [ ] Devpost submission form

## Judging weights
Technical depth 30% · Innovation 30% · Problem value 25% · Presentation 15%

## User (Ola) blockers — do these first, agent can't
1. Create Alibaba Cloud account (intl console) + activate Model Studio → get `DASHSCOPE_API_KEY` (free trial credits available)
2. Register on Devpost for the hackathon: https://qwencloud-hackathon.devpost.com/
3. Create a fresh PUBLIC GitHub repo (suggest `clearcrew`) — push from here when ready

## Build schedule
- **Jul 2–3**: skeleton (done), event log + agents + orchestrator working locally against DashScope
- **Jul 4–5**: conflict-resolution negotiation round, baseline single-agent, bench harness + results table (NB: Zero Cup R16 lock Jul 5 takes priority)
- **Jul 6**: deploy to Alibaba Cloud Function Compute, minimal web demo page (batch run + explain view)
- **Jul 7**: architecture diagram, README polish, record demo video
- **Jul 8**: Devpost submission (buffer day — deadline Jul 9 2pm PDT)

## Endpoint
DashScope OpenAI-compatible (intl): `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
Models: `qwen3.7-max` (agents/negotiation), `qwen3.7-plus` (intake triage, audit, cheap baseline comparisons)
