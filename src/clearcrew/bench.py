"""Benchmark: agent society vs single monolithic agent on the same labeled batch.

Configures an isolated event log, spawns each system in a separate subprocess
so LLM token counters, timing, and process memory never cross-contaminate.

Usage: DASHSCOPE_API_KEY=... python -m clearcrew.bench
"""
import copy
import json
import os
import subprocess
import sys
import time

from . import config, data, events, policy


def _verify(events_raw: list[dict]) -> dict:
    return events.verify_chain(events_raw)


def _run_in_subprocess(module: str, batch_json: str, event_log: str) -> dict:
    """Run a benchmark module in a subprocess with its own event log."""
    env = os.environ.copy()
    env["CLEARCREW_EVENT_LOG"] = event_log
    code = (
        f"import sys, json;"
        f"sys.path.insert(0, '{config.__file__[:-11]}');"
        f"from clearcrew.{module} import run_batch;"
        f"batch = json.loads(sys.argv[1]);"
        f"result = run_batch(batch);"
        f"print(json.dumps(result))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, batch_json],
        capture_output=True, text=True, timeout=600,
        env=env,
    )
    if proc.returncode != 0:
        stderr = proc.stderr[:500] if proc.stderr else "(no stderr)"
        raise RuntimeError(f"{module} subprocess failed: {stderr}")
    return json.loads(proc.stdout)


def _tokens(result: dict) -> int:
    """Token spend, carried back from the subprocess that actually made the calls."""
    u = result.get("usage") or {}
    return u.get("prompt_tokens", 0) + u.get("completion_tokens", 0)


def _score(decisions: dict[str, str], batch: list[dict]) -> float:
    correct = sum(1 for p in batch if decisions.get(p["id"], "?").startswith(p["_expected"][:6]))
    return correct / len(batch)


def run() -> None:
    batch = data.make_batch(n=int(os.environ.get("BATCH_N", "12")))
    clean = [{k: v for k, v in p.items() if k != "_expected"} for p in batch]
    clean_json = json.dumps(clean)

    # --- Society (subprocess) ---
    t0 = time.time()
    society_log = "events-society.jsonl"
    if os.path.exists(society_log):
        os.remove(society_log)
    society_events: list[dict] = []
    try:
        society_result = _run_in_subprocess("orchestrator", clean_json, society_log)
        with open(society_log) as f:
            society_events = [json.loads(line) for line in f if line.strip()]
        society_chain = _verify(society_events)
    except Exception as exc:
        print(f"Society subprocess failed: {exc}")
        society_result = {"state": {}, "explanations": {}}
        society_chain = {"hashed": False, "verified": False, "events": 0, "broken_at": None}
    society_secs = round(time.time() - t0, 1)
    # Score the society's PROPOSALS, not its terminal decisions.
    #
    # The policy gate refuses to record an approval the policy forbids, so
    # terminal outcomes now agree with policy by construction — scoring them
    # would report 100% forever and measure the gate instead of the agents.
    # The proposal is what the society actually judged, and it stays falsifiable.
    society_proposals = society_result.get("proposals", {})
    society_terminal = {pid: s["status"] for pid, s in society_result.get("state", {}).items()
                        if pid != "batch"}
    society_decisions = society_proposals or society_terminal   # pre-gate runs have no proposals
    society = {
        "seconds": society_secs,
        "tokens": _tokens(society_result),
        "accuracy": _score(society_decisions, batch),
        "scored_on": "proposals" if society_proposals else "terminal_decisions",
        "blocked_by_policy": sum(
            1 for e in society_events if e["type"] == "policy.blocked"),
        "auditable": True,
        "chain": society_chain,
    }

    # --- Monolith (subprocess) ---
    t0 = time.time()
    mono_log = "events-monolith.jsonl"
    if os.path.exists(mono_log):
        os.remove(mono_log)
    try:
        mono_result = _run_in_subprocess("baseline", clean_json, mono_log)
    except Exception as exc:
        print(f"Monolith subprocess failed: {exc}")
        mono_result = {"decisions": []}
    mono_secs = round(time.time() - t0, 1)
    mono_decisions = {d.get("payout_id"): ("approved" if d.get("action") == "approve" else "rejected")
                      for d in mono_result.get("decisions", [])}
    monolith = {
        "seconds": mono_secs,
        "accuracy": _score(mono_decisions, batch),
        "tokens": _tokens(mono_result),
        "auditable": False,
    }

    # --- Print results ---
    print(f"{'id':<10}{'amount':>8} {'corridor':<8}{'expected':<10}{'society':<10}{'monolith':<10}")
    for p in batch:
        soc = society_decisions.get(p["id"], "?")
        mono = mono_decisions.get(p["id"], "?")
        mark = "" if soc.startswith(p["_expected"][:6]) and mono.startswith(p["_expected"][:6]) else "  <-- miss"
        print(f"{p['id']:<10}{p['amount']:>8.0f} {p['from_country']+'-'+p['to_country']:<8}"
              f"{p['_expected']:<10}{soc:<10}{mono:<10}{mark}")
    print()
    print(f"{'':<12}{'accuracy':>10}{'tokens':>10}{'seconds':>10}{'auditable':>11}")
    for name, r in (("society", society), ("monolith", monolith)):
        print(f"{name:<12}{r['accuracy']:>10.0%}{r['tokens']:>10}{r['seconds']:>10}"
              f"{str(r['auditable']):>11}")

    # --- Archive society event log ---
    stamp = time.strftime("%Y%m%d-%H%M%S")
    os.makedirs("runs", exist_ok=True)
    dest = f"runs/events-{stamp}-n{len(batch)}.jsonl"
    events.export_jsonl(dest, src=society_log)
    with open(f"runs/results-{stamp}-n{len(batch)}.json", "w") as f:
        # both, because the gate can make them differ — a payout the society
        # proposed to approve and policy refused reads: society=approve,
        # society_terminal=rejected. That divergence is the whole point.
        per_payout = {p["id"]: {"expected": p["_expected"],
                                "society": society_decisions.get(p["id"]),
                                "society_terminal": society_terminal.get(p["id"]),
                                "monolith": mono_decisions.get(p["id"])}
                      for p in batch}
        json.dump({"society": society, "monolith": monolith,
                   "decisions": per_payout}, f, indent=2)
    print(f"\nrun archived: runs/events-{stamp}-n{len(batch)}.jsonl")
    for tmp in (society_log, mono_log):
        db = events._db_path(tmp)
        for f in (tmp, db, db + "-wal", db + "-shm"):  # WAL leaves sidecars
            if os.path.exists(f):
                os.remove(f)


if __name__ == "__main__":
    run()
