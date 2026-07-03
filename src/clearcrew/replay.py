"""Replay Time Machine: step through any payout's real event chain.

Reads archived event logs from runs/ — every event shown was emitted by a live
run of the society. Nothing is staged. This FastAPI app is also the backend
deployed to Alibaba Cloud Function Compute.
"""
import json
import os
import re
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from . import data, events as event_log, policy

RUNS_DIR = Path(os.environ.get("CLEARCREW_RUNS_DIR", Path(__file__).parent.parent / "runs"))
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="ClearCrew Replay Time Machine")

_RUN_RE = re.compile(r"^events-(?P<stamp>[\w-]+?)-n(?P<n>\d+)\.jsonl$")


def _list_runs() -> list[dict]:
    runs = []
    for p in sorted(RUNS_DIR.glob("events-*.jsonl")):
        m = _RUN_RE.match(p.name)
        if not m:
            continue
        run = {"name": p.name, "stamp": m["stamp"], "n": int(m["n"]), "results": None}
        results_path = RUNS_DIR / p.name.replace("events-", "results-").replace(".jsonl", ".json")
        if results_path.exists():
            run["results"] = json.loads(results_path.read_text())
        runs.append(run)
    return runs


def _load_events(run_name: str) -> list[dict]:
    if "/" in run_name or not _RUN_RE.match(run_name):
        raise HTTPException(404, "no such run")
    path = RUNS_DIR / run_name
    if not path.exists():
        raise HTTPException(404, "no such run")
    with open(path) as f:
        events = [json.loads(line) for line in f if line.strip()]
    # file order is emission order (hash chain verifies against it);
    # stable sort by ts preserves it for equal timestamps
    return sorted(events, key=lambda e: e["ts"])


_chain_cache: dict[str, dict] = {}


def _verify(run_name: str, events: list[dict]) -> dict:
    """Chain verification, cached — archived run files are immutable."""
    if run_name not in _chain_cache:
        _chain_cache[run_name] = event_log.verify_chain(events)
    return _chain_cache[run_name]


def _batch_lookup(n: int) -> dict[str, dict]:
    """The benchmark batch is deterministic (seed 7), so payout details can be
    reconstructed exactly for enrichment — same IDs, same amounts."""
    return {p["id"]: p for p in data.make_batch(n)}


@app.get("/healthz")
def healthz():
    return {"ok": True, "runs": len(_list_runs())}


@app.get("/api/runs")
def list_runs():
    return {"runs": _list_runs()}


@app.get("/api/runs/{run_name}")
def run_detail(run_name: str):
    events = _load_events(run_name)
    m = _RUN_RE.match(run_name)
    lookup = _batch_lookup(int(m["n"]))
    t0 = events[0]["ts"] if events else 0.0

    payouts: dict[str, dict] = {}
    for e in events:
        s = e["subject"]
        if s == "batch":
            continue
        p = payouts.setdefault(s, {"id": s, "status": "pending", "events": 0, "disputed": False})
        p["events"] += 1
        if e["type"] in ("payout.approved", "payout.rejected", "payout.settled"):
            p["status"] = e["type"].split(".", 1)[1]
        if e["type"] == "dispute.resolved":
            p["disputed"] = True

    for pid, p in payouts.items():
        detail = lookup.get(pid)
        if detail:
            p.update(
                amount=detail["amount"],
                currency=detail["currency"],
                corridor=f"{detail['from_country']}→{detail['to_country']}",
                recipient_age_days=detail["recipient_age_days"],
                memo=detail["memo"],
                expected=detail["_expected"],
            )
            p["miss"] = (p["status"] == "approved") != (detail["_expected"] == "approve")

    ordered = sorted(payouts.values(), key=lambda p: (-p["disputed"], -(p.get("amount") or 0)))
    return {"run": run_name, "t0": t0, "total_events": len(events),
            "chain": _verify(run_name, events), "payouts": ordered}


@app.get("/api/runs/{run_name}/explain/{subject}")
def explain(run_name: str, subject: str):
    events = _load_events(run_name)
    t0 = events[0]["ts"] if events else 0.0
    chain = [e for e in events if e["subject"] == subject]
    if not chain:
        raise HTTPException(404, "no events for that subject")
    m = _RUN_RE.match(run_name)
    detail = _batch_lookup(int(m["n"])).get(subject)
    return {
        "subject": subject,
        "payout": detail,
        "verification": _verify(run_name, events),
        "chain": [{**e, "t_offset": round(e["ts"] - t0, 2)} for e in chain],
    }


@app.get("/api/runs/{run_name}/counterfactual")
def counterfactual(run_name: str, reserve_floor: float | None = None,
                   p2_amount: float | None = None, p2_age_days: int | None = None):
    """Deterministic counterfactual replay: fold the SAME recorded batch through
    a hypothetical policy version. Only the mechanical layer (P1/P2/P3 over
    known amounts) is re-evaluated — recorded agent judgments are replayed
    as-is, never re-generated. Executable history, not prediction."""
    events = _load_events(run_name)
    m = _RUN_RE.match(run_name)
    batch = data.make_batch(int(m["n"]))

    in_force = policy.CURRENT
    overrides = {k: v for k, v in (("reserve_floor", reserve_floor),
                                   ("p2_amount", p2_amount),
                                   ("p2_age_days", p2_age_days)) if v is not None}
    hypothetical = replace(in_force, version=f"{in_force.version}+counterfactual",
                           reason="hypothetical — evaluated, never enacted", **overrides)

    base = policy.evaluate(batch, in_force)
    hypo = policy.evaluate(batch, hypothetical)
    recorded = {e["subject"]: e["type"].split(".", 1)[1] for e in events
                if e["type"] in ("payout.approved", "payout.rejected")}
    amounts = {p["id"]: p["amount"] for p in batch}

    changes = []
    for pid in amounts:
        if base[pid] != hypo[pid]:
            b, h = base[pid], hypo[pid]
            changes.append({
                "payout_id": pid, "amount": amounts[pid],
                "recorded_outcome": recorded.get(pid),
                "in_force": b, "hypothetical": h,
                "cause": f"rule {h['rule'] or b['rule']} under changed parameters",
            })

    def tally(verdicts):
        approved = sum(1 for v in verdicts.values() if v["verdict"] == "approve")
        return {"approve": approved, "reject": len(verdicts) - approved}

    return {
        "run": run_name,
        "note": ("deterministic policy layer only — recorded agent judgments are "
                 "replayed as-is, never re-generated"),
        "policy_in_force": in_force.params(),
        "policy_hypothetical": hypothetical.params(),
        "summary": {"in_force": tally(base), "hypothetical": tally(hypo)},
        "changes": sorted(changes, key=lambda c: -c["amount"]),
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text()
