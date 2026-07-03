"""The MCP bridge must expose exactly the replay read paths — same data,
tool-shaped. Tools are plain functions, so they're tested directly."""
import pytest

from clearcrew import mcp_server


def test_tools_registered():
    names = {t.name for t in mcp_server.mcp._tool_manager.list_tools()}
    assert names == {"list_runs", "get_run", "explain_payout", "verify_run", "get_policy"}


def test_list_runs_matches_replay():
    runs = mcp_server.list_runs()["runs"]
    assert runs and all("name" in r and "n" in r for r in runs)


def test_explain_payout_returns_recorded_chain():
    run = mcp_server.list_runs()["runs"][-1]["name"]
    payouts = mcp_server.get_run(run)["payouts"]
    out = mcp_server.explain_payout(run, payouts[0]["id"])
    assert out["chain"] and all(e["subject"] == payouts[0]["id"] for e in out["chain"])
    assert "verification" in out


def test_verify_run_reports_chain_state():
    run = mcp_server.list_runs()["runs"][-1]["name"]
    v = mcp_server.verify_run(run)
    assert {"hashed", "verified", "events"} <= set(v)


def test_bad_run_is_plain_tool_error():
    with pytest.raises(ValueError):
        mcp_server.get_run("../../etc/passwd")
    with pytest.raises(ValueError):
        mcp_server.explain_payout("events-nope-n36.jsonl", "abc")


def test_get_policy_is_the_agents_policy():
    from clearcrew.policy import PAYOUT_POLICY
    assert mcp_server.get_policy() == PAYOUT_POLICY
