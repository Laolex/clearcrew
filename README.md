# ClearCrew

**Autonomous agents are hard to trust with money because their decisions vanish
the moment they're made — no trail to replay, no reasoning to audit, no specific
agent to fix.**

**ClearCrew replaces the opaque single-agent decision with a society of five
specialist Qwen agents whose disagreements, vetoes, and negotiated resolutions
are recorded as replayable, hash-chained history. Starting with payout
operations.**

Built on Qwen Cloud for the Global AI Hackathon Series (Agent Society track).
Five specialist agents — Intake, Compliance, Treasury, Resolution, Auditor —
divide a batch of payout requests through task decomposition and negotiated
conflict resolution. Every decision is an event in an append-only log: state is a
fold over events, and any outcome can be replayed and explained.

This is not a diagram — it's four events from a recorded run
(`runs/events-20260703-165045-settled-n6.jsonl`, payout `1818e811`, trimmed
for width; the chain is global, so events from other payouts sit between
these). An agent's judgment, the final verdict, and the **real on-chain
settlement it caused** — every event committing to the hash of the one
before it in the log:

```jsonc
{"type":"treasury.decided",    "actor":"treasury",     "payload":{"action":"pay_now","reason":"Cumulative total 11500.0 <= headroom 90000.0"},
 "prev_hash":"254a6bb6…", "event_hash":"9f7548e9…"}
{"type":"payout.approved",     "actor":"orchestrator", "payload":{},
 "prev_hash":"ac3bbae8…", "event_hash":"b1d8e01f…"}
{"type":"settlement.confirmed","actor":"verasettle",   "payload":{"source_amount_usd":9800.0,"settled_amount_usdc":0.98,
   "scale":"1:10000 testnet conversion (recorded, not implied)","chain":"BASE-SEPOLIA",
   "tx_hash":"0xee004e0813fd239840821471f5c70752bb963264df3cfea65dbeab37a7d96866"},
 "prev_hash":"b8e986dd…", "event_hash":"da0d55de…"}
{"type":"payout.settled",      "actor":"orchestrator", "payload":{"tx_hash":"0xee004e08…","chain":"BASE-SEPOLIA"},
 "prev_hash":"da0d55de…", "event_hash":"447f28c8…"}
```

Tamper with any earlier event — the reason, the amount, the verdict — and
`events.verify_chain` breaks at that index. The tx hash is checkable on any
Base Sepolia RPC. That's the whole thesis in one screenful: **judgment,
verdict, and money movement in one tamper-evident history.**

```
batch → Intake (triage, qwen-turbo)
      → Compliance (veto power, qwen-max)   ─┐ disputes → Resolution agent
      → Treasury (funding/batching)          ─┘ (structured negotiation, recorded)
      → Auditor (plain-English explanation of every payout's event chain)
```

## Why specialization + provenance beats an opaque monolith

The claim is not that five agents are smarter than one big one. It's that when
the monolith errs, you cannot locate responsibility — there is no *why* to
retrieve, no agent to fix, no record to check. The society produces
**accountable failure**: every error is attributed to a specific agent, with
its reasoning on the record, contradicted or confirmed by the events around it.

![Accountable failure](docs/accountable-failure.png)

Both systems wrongly rejected the same clean $5,000 payout at some point in
these benchmarks. The monolith's rejection is a dead end. The society's is a
five-event recorded chain in which its own Auditor flags Treasury's reasoning
as incorrect — which is what told us which agent to fix.

`python -m clearcrew.bench` runs the same labeled batch through the society and
through a single monolithic agent. Both receive the identical org policy AND the
same deterministic arithmetic aids; the labels model the full policy, including
the reserve-floor funding waterfall.

**Headline run** (`runs/events-20260702-210640-n36.jsonl`, hash chain verified):

| batch | system | accuracy | tokens | seconds | auditable |
|---|---|---|---|---|---|
| n=12 | society | 100% | 21,992 | 146 | ✓ |
| n=12 | monolith | 100% | 3,894 | 54 | ✗ |
| n=36 | society | **100%** | 76,113 | 323 | ✓ |
| n=36 | monolith | **89%** | 12,068 | 150 | ✗ |

At n=36 the monolith fails silently in both directions: it approves $30,000 of
payouts that breach the treasury reserve floor, and rejects two perfectly clean
$5,000 payouts with no recoverable explanation. The society gets all 36 right,
and every one of its decisions has a replayable, hash-verified event trail.

### The repair ladder

We publish every n=36 run, including the ones where the society lost — because
each regression was diagnosed *from the recorded trail* and fixed with
governance, not prompt-tweaking:

| run | governance in place | society | monolith | what the trail caught |
|---|---|---|---|---|
| 1 | written policy · cited vetoes · separation of duties | 100% | 89% | (earlier: Treasury hallucinating P2 — caught in-band by the Auditor) |
| 2 | same, fresh run (first hash-chained) | 94% | 92% | Treasury judging payouts individually — "sufficient balance" ×24, floor breached |
| 3 | + **agents judge, ledgers add**: deterministic cumulative ledger for both systems | 97% | 89% | Treasury's recorded reason ends "…Reject." while its action says `pay_now` — a reason/action self-contradiction, machine-checkable |
| 4 | + **code flags, agents rule**: every treasury decision reconciled against the ledger; mismatches become recorded disputes ruled by Resolution | **100%** | 89% | chain verified, guard armed (did not need to fire) |

The monolith wobbles run-to-run (89–92%) and there is nothing to read, nobody
to fix. That's the actual claim: the trail is not just explanation — it's
*repair*. See `docs/demo-notes.md` for the full event chains behind each row.

## Replay Time Machine

![Replay Time Machine](docs/replay-time-machine.png)

**Live demo: https://clearcrew.verasettle.com** (backed by Alibaba Cloud
Function Compute — see `deploy/`).

Every run archives its full event log to `runs/`. The Replay Time Machine steps
through any payout's real event chain — intake triage, compliance veto with the
policy rule cited, the recorded dispute-resolution ruling, the final verdict, and
the auditor's plain-English explanation. Real payout IDs, real model output,
nothing staged. Deep-linkable: `#<run>/<payout_id>`.

Replay reconstructs recorded history — it never re-runs models or simulates
alternate outcomes.

## Executable policy — counterfactual replay

![Counterfactual replay](docs/counterfactual-replay.png)

Policy is data, not prose: a versioned `PolicyVersion` renders the binding text
the agents are prompted with, and `policy.evaluate()` — the same function that
labels the benchmark's ground truth — computes what the written rules say for
any batch. New runs open with a `policy.enacted` event recording the version
and parameters in force (archived runs predate this and honestly lack it).

That makes history *executable*: the replay UI and API can fold a run's
recorded batch through hypothetical parameters — raise the reserve floor,
move the P2 threshold — and show exactly which payouts would flip, and under
which rule. Strictly the deterministic layer: recorded agent judgments are
replayed as-is, never re-generated. Not prediction — arithmetic over history.

```
GET /api/runs/<run>/counterfactual?reserve_floor=40000
```

```bash
cd src && uvicorn clearcrew.replay:app --port 9000   # then open http://localhost:9000
```

## From verdict to movement — real testnet settlement

![Settled on-chain](docs/settled-on-chain.png)

The society's verdicts don't stop at "approved" — run
`python -m clearcrew.settle_demo` and every approved payout is executed as a
**real USDC transfer on Base Sepolia** through [Verasettle](https://verasettle.com)
(a non-custodial USDC payout orchestrator) as the settlement rail. The
settlement lives in the same hash-chained history as the decision that caused
it: `settlement.requested` → `settlement.confirmed` (on-chain tx hash + rail
receipt id + receipt content hash) → `payout.settled`.

Archived run `runs/events-20260703-165045-settled-n6.jsonl` (chain verified,
41 events): the society vetoed a sanctioned-corridor payout, rejected two P2
violations, and settled the three clean payouts on-chain — 6/6 against ground
truth. Verify the transfers yourself on any Base Sepolia RPC:

| payout | source | settled | tx |
|---|---|---|---|
| 6513270e | $850 | 0.085 USDC | [`0xea031e…`](https://sepolia.basescan.org/tx/0xea031ed652f5c8d7bfae7117832b32847fe655429ed6f5e8a247da101be318cd) |
| 1818e811 | $9,800 | 0.98 USDC | [`0xee004e…`](https://sepolia.basescan.org/tx/0xee004e0813fd239840821471f5c70752bb963264df3cfea65dbeab37a7d96866) |
| 099950d8 | $850 | 0.085 USDC | [`0x8ccd4f…`](https://sepolia.basescan.org/tx/0x8ccd4f77e52852ba0ab7e5b0db1bb0288ecf3fb28665a8c61ae317bb567b1cea) |

Honesty notes, as always: benchmark USD amounts settle at an explicitly
recorded 1:10,000 testnet conversion — every event carries both figures and
the scale; nothing is implied. Rail failures are recorded as
`settlement.failed` events, never silently retried or hidden.

## MCP server — the audit trail as tools

The same read paths the Replay Time Machine uses are exposed as an MCP server,
so any MCP-capable agent framework (Qwen, Claude, anything) can interrogate
ClearCrew's recorded history as tools — `list_runs`, `get_run`,
`explain_payout`, `verify_run`, `get_policy`, `counterfactual_policy`
(deterministic what-if over the recorded batch). Read-only, no model calls, no
API key needed: an orchestrator asks *why* a payout was rejected and gets the
hash-verified event chain back, not a summary someone wrote after the fact.
Full docs with real session transcripts: [docs/MCP.md](docs/MCP.md).

```bash
cd src && python -m clearcrew.mcp_server        # stdio transport
```

```json
{ "mcpServers": { "clearcrew": {
    "command": "python", "args": ["-m", "clearcrew.mcp_server"],
    "cwd": "<repo>/src" } } }
```

## Try it yourself (no setup → full setup)

1. **Zero setup — the live demo**: https://clearcrew.verasettle.com — pick the
   `settled` run, click any payout, step its chain (arrow keys). Deep link to
   the on-chain one: [`#…-settled-n6.jsonl/1818e811`](https://clearcrew.verasettle.com/#events-20260703-165045-settled-n6.jsonl/1818e811).
2. **Verify a settlement independently** — don't trust us, ask the chain:
   ```bash
   curl -s https://sepolia.base.org -H 'content-type: application/json' -d \
     '{"jsonrpc":"2.0","id":1,"method":"eth_getTransactionReceipt","params":["0xee004e0813fd239840821471f5c70752bb963264df3cfea65dbeab37a7d96866"]}'
   ```
3. **Verify the hash chain yourself** (clone, no API key needed):
   ```bash
   pip install -r requirements-dev.txt && cd src
   python -c "import json; from clearcrew import events; \
     print(events.verify_chain([json.loads(l) for l in open('runs/events-20260703-165045-settled-n6.jsonl')]))"
   python -m pytest tests/ -q        # 38 tests
   ```
4. **Query history as an agent** — the [MCP server](docs/MCP.md), read-only,
   keyless.
5. **Re-run the benchmark or the settlement demo** — needs your own
   `DASHSCOPE_API_KEY` (and a Verasettle sandbox for settlement); see below.
   Recorded runs in `runs/` are the originals — reruns produce new history,
   they never overwrite it.

## Run the benchmark

```bash
pip install -r requirements.txt
export DASHSCOPE_API_KEY=sk-...   # Qwen Cloud / Model Studio key
cd src && python -m clearcrew.bench   # BATCH_N=36 for the large batch
```

## Production posture

- **Resilient LLM calls**: SDK-level timeout and retry-with-backoff on transient
  faults; malformed model JSON gets one re-ask then fails loudly — a payout never
  proceeds on a half-parsed decision (`llm.ModelResponseError`). (The timeout must
  exceed the worst-case legitimate call: the monolith baseline reasons over an
  entire batch in ONE ~140s request — operationally fragile in exactly the way
  its decisions are unauditable.)
- **Agents judge, ledgers add**: cumulative funding arithmetic is computed
  deterministically in code (`agents.build_ledger`) and handed to the models —
  both the society's Treasury and the monolith baseline. A judgment engine is
  never asked to be a calculator.
- **Fail-safe defaults**: any payout without an explicit final decision is
  rejected-by-default, with the reason on the record.
- **Tests**: `pytest src/tests/` — ground-truth labeling invariants (including
  the reserve-floor waterfall), event-log fold/explain/replay invariants, and
  every replay API endpoint including path-traversal rejection.
- **Deployable**: containerized (see `Dockerfile`), `/healthz` endpoint, all
  config via environment variables, secrets never in the repo.
- **Honest scope**: this is a working trust-layer demonstration; hooking it to
  real money movement would additionally need API auth, idempotency keys, and a
  durable event store in place of JSONL files.

```bash
pip install -r requirements-dev.txt && cd src && python -m pytest tests/
```

## Roadmap (direction, not claims)

V1 proved that recorded history makes an agent system explainable — and, read
carefully, repairable. V2 (in this repo) made policy versioned and history
executable: `policy.enacted` events, and deterministic counterfactual replay
in the UI, API, and MCP server. What's next:

1. **Durable event store + pluggable anchoring** — JSONL → append-only store,
   head hash anchored via a provider interface (RFC-3161 TSA default). Recorded
   history stays immutable; repairs only ever arrive as new events.
2. **Evidence packs** — an exportable, offline-verifiable bundle per run
   (events, policy version, chain head, verification report) that an auditor
   can check without trusting this codebase or any network service.

## Stack

- **Models**: `qwen3.7-max` (reasoning roles), `qwen3.7-plus` (triage/audit) via Qwen Cloud
  DashScope OpenAI-compatible endpoint
- **Deploy**: **live on Alibaba Cloud Function Compute 3.0** —
  https://clearcrw-replay-ilccmqckdu.ap-southeast-1.fcapp.run (public read-only
  API; see `deploy/` for the FC handler + IaC, or `Dockerfile` for the
  container path)
- **Provenance**: append-only, hash-chained JSONL event log — each event commits
  to its predecessor's hash, so recorded history is tamper-evident (`events.verify_chain`);
  `events.explain(id)` reconstructs any payout's causal chain. (External anchoring of
  the head hash would make runs independently verifiable — that's the roadmap, not a claim.)

## License

MIT
