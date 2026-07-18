"""MCP server: ClearCrew's audit trail as tools for any agent framework.

A thin bridge over the same read-only code paths the Replay Time Machine uses —
no new logic, no model calls, no key required. An orchestrator (Claude, Qwen,
anything MCP-capable) can ask *why* a payout was approved or rejected and get
the recorded, hash-verified event chain back, not a summary someone wrote.

Run over stdio:  python -m clearcrew.mcp_server
"""
from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP

from . import replay
from . import policy

mcp = FastMCP(
    "clearcrew",
    instructions=(
        "Read-only audit trail of ClearCrew payout runs. Every event was "
        "recorded live by the agent society; nothing is generated on request. "
        "Use explain_payout to retrieve a payout's causal chain and "
        "verify_run to check the hash chain before trusting it."
    ),
)


def _unwrap(fn, *args):
    """Replay endpoints raise HTTPException; surface those as plain tool errors."""
    try:
        return fn(*args)
    except HTTPException as e:
        raise ValueError(e.detail) from e


def list_runs() -> dict:
    """List archived benchmark runs, newest last, with benchmark results where
    recorded (society vs monolith accuracy/tokens/seconds)."""
    return {"runs": replay._list_runs()}


def get_run(run_name: str) -> dict:
    """Full detail for one run: hash-chain verification plus every payout's
    status, amount, corridor, expected label, and whether it was disputed.
    run_name is a file name from list_runs, e.g. 'events-20260702-210640-n36.jsonl'."""
    return _unwrap(replay.run_detail, run_name)


def explain_payout(run_name: str, payout_id: str) -> dict:
    """The recorded causal chain for one payout: intake triage, compliance
    verdict with the policy rule cited, treasury decision, any recorded
    dispute-resolution ruling, and the auditor's plain-English explanation.
    Includes chain verification — reconstructed history, never re-generated."""
    return _unwrap(replay.explain, run_name, payout_id)


def verify_run(run_name: str) -> dict:
    """Verify a run's hash chain (each event commits to its predecessor).
    Returns hashed/verified flags, the event count, and the index where the
    chain breaks, if it does. Runs recorded before hash chaining honestly
    report hashed=false rather than pretending."""
    events = _unwrap(replay._load_events, run_name)
    return replay._verify(run_name, events)


def get_policy() -> str:
    """The written org policy given verbatim to every agent AND to the
    monolith baseline — the ground truth that vetoes must cite."""
    return policy.CURRENT.render()


def counterfactual_policy(run_name: str, reserve_floor: float | None = None,
                          p2_amount: float | None = None,
                          p2_age_days: int | None = None) -> dict:
    """Deterministic counterfactual replay: what would the written policy have
    ruled for this run's recorded batch under different parameters (reserve
    floor, P2 amount threshold, P2 recipient-age cutoff)? Re-folds ONLY the
    mechanical policy layer — recorded agent judgments are never re-generated.
    Returns per-payout diffs with the rule that caused each change."""
    return _unwrap(lambda: replay.counterfactual(run_name, reserve_floor,
                                                 p2_amount, p2_age_days))


for _fn in (list_runs, get_run, explain_payout, verify_run, get_policy,
            counterfactual_policy):
    mcp.tool()(_fn)


if __name__ == "__main__":
    mcp.run()
