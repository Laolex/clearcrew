# ClearCrew MCP server — the audit trail as tools

Any MCP-capable agent (Claude, Qwen, custom orchestrators) can interrogate
ClearCrew's recorded history as tools. This is the point of treating history
as first-class state: the primary consumer of an audit trail isn't a human
with a dashboard — it's other agents, auditors, and policy engines.

**Read-only by design.** There is deliberately no tool that settles, approves,
or writes anything. An external agent can *interrogate* history, never *make*
it — the opposite would be the exact failure mode this project argues against.
No API key or model access is needed; the tools read archived runs.

## Run it

```bash
pip install -r requirements.txt
cd src && python -m clearcrew.mcp_server        # stdio transport
```

Client config (Claude Code: `claude mcp add clearcrew -- python -m clearcrew.mcp_server`
from `src/`, or any MCP client):

```json
{
  "mcpServers": {
    "clearcrew": {
      "command": "python",
      "args": ["-m", "clearcrew.mcp_server"],
      "cwd": "<repo>/src"
    }
  }
}
```

## Tools

| tool | arguments | returns |
|---|---|---|
| `list_runs` | — | archived runs with benchmark results where recorded |
| `get_run` | `run_name` | chain verification + every payout's status/amount/expected/disputed |
| `explain_payout` | `run_name`, `payout_id` | the payout's full recorded causal chain, with verification |
| `verify_run` | `run_name` | hash-chain check: `hashed`/`verified`/`events`/`broken_at` |
| `get_policy` | — | the binding org policy text every agent was prompted with |
| `counterfactual_policy` | `run_name`, `reserve_floor?`, `p2_amount?`, `p2_age_days?` | deterministic what-if over the recorded batch, per-payout diffs |

## Real session (verbatim tool output, not mocked)

`verify_run("events-20260702-210640-n36.jsonl")` — the headline benchmark run:

```json
{"hashed": true, "verified": true, "events": 179, "broken_at": null}
```

`explain_payout("events-20260703-165045-settled-n6.jsonl", "1818e811")` — a
payout that settled real testnet USDC (chain excerpt; full response includes
every event and the verification block):

```json
{"type": "settlement.confirmed", "actor": "verasettle",
 "payload": {"source_amount_usd": 9800.0, "settled_amount_usdc": 0.98,
             "scale": "1:10000 testnet conversion (recorded, not implied)",
             "chain": "BASE-SEPOLIA",
             "tx_hash": "0xee004e0813fd239840821471f5c70752bb963264df3cfea65dbeab37a7d96866"}}
```

`counterfactual_policy("events-20260702-210640-n36.jsonl", reserve_floor=40000)`:

```json
{"summary": {"in_force": {"approve": 22, "reject": 14},
             "hypothetical": {"approve": 19, "reject": 17}},
 "changes": "… three $9,800 payouts flip approve→reject, rule P3 …",
 "note": "deterministic policy layer only — recorded agent judgments are replayed as-is, never re-generated"}
```

Malformed input comes back as a clean tool error, not a crash — path traversal
(`get_run("../../etc/passwd")`) is rejected, and every tool is covered by the
test suite (`src/tests/test_mcp.py`).
