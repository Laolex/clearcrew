# For coding agents integrating this repo

Read this before crawling the tree; it saves you the exploration.

## Layout

- `src/clearcrew/` — the package. No build step, no framework beyond FastAPI.
- `src/runs/` — **immutable recorded history**. Never edit, regenerate, or
  "fix" these files; reruns create new files. Hash chains break loudly if you
  touch them (`events.verify_chain`).
- `src/tests/` — pytest; run from `src/`: `python -m pytest tests/ -q`.
  No API key needed for tests, the replay server, or the MCP server.

## The pieces you can lift independently

| module | import surface | depends on |
|---|---|---|
| `clearcrew.events` | `emit`, `fold_state`, `explain`, `verify_chain`, `read_all` | stdlib only |
| `clearcrew.policy` | `PolicyVersion`, `evaluate`, `CURRENT`, `VERSIONS` | stdlib only |
| `clearcrew.settlement` | `settle_payout`, `usdc_amount`, `SettlementError` | stdlib only (urllib) |
| `clearcrew.mcp_server` | 6 read-only tools over the trail | `mcp`, `clearcrew.replay` |
| `deploy/fc_handler.py` | Alibaba FC HTTP-event → ASGI adapter | your ASGI app |

## Invariants you must not break

1. **Append-only.** State is `fold(events)`; nothing ever updates or deletes
   an event. Corrections are new events.
2. **Replay ≠ recompute.** Replay reconstructs recorded history; it never
   re-runs models. Counterfactuals re-fold ONLY the deterministic policy layer.
3. **`policy.PAYOUT_POLICY` text is byte-stable.** Archived runs were prompted
   with exactly this rendering; `test_rendered_text_stable` guards it.
4. **Nothing staged.** Every figure shown anywhere must come from a recorded
   run. If you add UI, render real events or nothing.
5. **Secrets:** `.env` (gitignored) holds `DASHSCOPE_API_KEY` and optional
   `VERASETTLE_*`. Never emit them into events, logs, or docs.

## Common tasks

- Add an event type: emit it (`events.emit(type, subject, actor, payload)`),
  teach `static/index.html` its rendering + fold label, add a test.
- New benchmark run: `cd src && BATCH_N=36 python -m clearcrew.bench`
  (needs `DASHSCOPE_API_KEY`; archives itself into `runs/`).
- Deploy: see `deploy/README.md` (Serverless Devs; the FC gotchas are in
  `GOTCHAS.md` and they WILL bite you otherwise).
