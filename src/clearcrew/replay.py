"""Replay Time Machine: step through any payout's real event chain.

Reads archived event logs from runs/ — every event shown was emitted by a live
run of the society. Nothing is staged. This FastAPI app is also the backend
deployed to Alibaba Cloud Function Compute.

Judge mode (/api/live/*) only works where the secrets live: it spawns a real
settle_demo run (live Qwen calls + real testnet settlement) on the host, so it
is enabled only when CLEARCREW_JUDGE_CODE is set — never on the FC deployment.
"""
import functools
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from . import data, events as event_log, policy

API_TOKEN = os.environ.get("CLEARCREW_API_TOKEN", "")

RUNS_DIR = Path(os.environ.get("CLEARCREW_RUNS_DIR", Path(__file__).parent.parent / "runs"))
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="ClearCrew Replay Time Machine")

_RUN_RE = re.compile(r"^events-(?P<stamp>[\w-]+?)-n(?P<n>\d+)\.jsonl$")


def require_auth(authorization: str | None = Header(None)) -> None:
    if not API_TOKEN:
        return
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="missing or invalid API token")


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


def _scan_all_runs() -> dict:
    """Walk every archived run once; return the aggregates that power the
    Overview / Failures / Analytics views. All values are recorded facts —
    nothing is synthesized."""
    out = {"runs": [], "payouts": [], "vetoes": [], "treasury_rejects": [],
           "disputes": [], "settlements": []}
    for meta in _list_runs():
        name = meta["name"]
        events = _load_events(name)
        lookup = _batch_lookup(meta["n"])
        out["runs"].append({**{k: meta[k] for k in ("name", "stamp", "n", "results")},
                            "chain": _verify(name, events)})
        payouts: dict[str, dict] = {}
        for e in events:
            s, P = e["subject"], e.get("payload", {})
            if s == "batch":
                continue
            p = payouts.setdefault(s, {"run": name, "id": s, "status": "pending",
                                       "disputed": False, "settled": False, "usdc": None,
                                       "tx_hash": None, "explorer": None, "last_ts": e["ts"]})
            p["last_ts"] = max(p["last_ts"], e["ts"])
            if e["type"] in ("payout.approved", "payout.rejected", "payout.settled"):
                p["status"] = e["type"].split(".", 1)[1]
            if e["type"] == "payout.settled":
                p["settled"] = True
            if e["type"] == "dispute.resolved":
                p["disputed"] = True
                out["disputes"].append({"run": name, "id": s,
                                        "ruling": P.get("ruling"), "reason": P.get("reason")})
            if e["type"] == "compliance.reviewed" and P.get("verdict") == "veto":
                out["vetoes"].append({"run": name, "id": s, "rule": P.get("policy_rule"),
                                      "reason": P.get("reason")})
            if e["type"] == "treasury.decided" and P.get("action") not in ("pay_now", "pay"):
                out["treasury_rejects"].append({"run": name, "id": s, "reason": P.get("reason")})
            if e["type"] == "settlement.confirmed":
                p["usdc"] = P.get("settled_amount_usdc")
                p["tx_hash"] = P.get("tx_hash")
                p["explorer"] = P.get("explorer")
                out["settlements"].append({"run": name, "id": s,
                                           "usdc": P.get("settled_amount_usdc"),
                                           "tx_hash": P.get("tx_hash"),
                                           "explorer": P.get("explorer"),
                                           "chain": P.get("chain"),
                                           "source_usd": P.get("source_amount_usd")})
        for pid, p in payouts.items():
            d = lookup.get(pid)
            if d:
                p["amount"] = d["amount"]
                p["corridor"] = f"{d['from_country']}→{d['to_country']}"
                p["recipient_age_days"] = d["recipient_age_days"]
                p["expected"] = d["_expected"]
                p["miss"] = (p["status"] in ("approved", "settled")) != (d["_expected"] == "approve")
            else:
                p.setdefault("amount", None)
                p.setdefault("miss", False)
        # backfill amount onto the failure records now that lookup is applied
        for bucket in ("vetoes", "treasury_rejects", "disputes"):
            for rec in out[bucket]:
                if rec["run"] == name and "amount" not in rec:
                    rec["amount"] = payouts.get(rec["id"], {}).get("amount")
        out["payouts"].extend(payouts.values())
    return out


@app.get("/healthz")
def healthz():
    return {"ok": True, "runs": len(_list_runs())}


@app.get("/api/runs")
def list_runs(auth=Depends(require_auth)):
    return {"runs": _list_runs()}


@app.get("/api/runs/{run_name}")
def run_detail(run_name: str, auth=Depends(require_auth)):
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
            p["miss"] = (p["status"] in ("approved", "settled")) != (detail["_expected"] == "approve")

    ordered = sorted(payouts.values(), key=lambda p: (-p["disputed"], -(p.get("amount") or 0)))
    return {"run": run_name, "t0": t0, "total_events": len(events),
            "chain": _verify(run_name, events), "payouts": ordered}


@app.get("/api/runs/{run_name}/explain/{subject}")
def explain(run_name: str, subject: str, auth=Depends(require_auth)):
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
                   p2_amount: float | None = None, p2_age_days: int | None = None,
                   auth=Depends(require_auth)):
    """Deterministic counterfactual replay: fold the SAME recorded batch through
    a hypothetical policy version. Only the mechanical layer (P1/P2/P3 over
    known amounts) is re-evaluated — recorded agent judgments are replayed
    as-is, never re-generated. Executable history, not prediction."""
    # the frontend's `min`/`max` on the number inputs are UX hints only — this
    # button fires a manual fetch(), not a <form> submit, so HTML5 constraint
    # validation never runs. This is the actual, only enforcement.
    for name, val in (("reserve_floor", reserve_floor), ("p2_amount", p2_amount), ("p2_age_days", p2_age_days)):
        if val is not None and val < 0:
            raise HTTPException(422, f"{name} must be zero or positive")
    if p2_age_days is not None and p2_age_days > 365:
        raise HTTPException(422, "p2_age_days must be 365 or fewer")
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


@app.get("/api/overview")
def overview(auth=Depends(require_auth)):
    scan = _scan_all_runs()
    hashed = [r["chain"] for r in scan["runs"] if r["chain"]["hashed"]]
    verified = [c for c in hashed if c["verified"]]
    payouts = scan["payouts"]
    totals = {
        "runs": len(scan["runs"]),
        "payouts": len(payouts),
        "settlements": len(scan["settlements"]),
        "usdc_moved": round(sum(s["usdc"] or 0 for s in scan["settlements"]), 6),
        "replay_pct": 100.0 if payouts else 0.0,
        "hash_verified_pct": round(100 * len(verified) / len(hashed), 1) if hashed else 0.0,
    }
    recent = sorted(payouts, key=lambda p: p["last_ts"], reverse=True)[:15]
    recent = [{"run": p["run"], "id": p["id"], "amount": p.get("amount"),
               "status": p["status"], "settled": p["settled"],
               "disputed": p["disputed"], "miss": p.get("miss", False)} for p in recent]
    return {"totals": totals, "recent": recent}


@app.get("/api/failures")
def failures(auth=Depends(require_auth)):
    scan = _scan_all_runs()
    vetoes = [{"run": v["run"], "id": v["id"], "amount": v.get("amount"),
               "reason": v.get("reason")} for v in scan["vetoes"]]
    trej = [{"run": t["run"], "id": t["id"], "amount": t.get("amount"),
             "reason": t.get("reason")} for t in scan["treasury_rejects"]]
    disp = [{"run": d["run"], "id": d["id"], "amount": d.get("amount"),
             "reason": d.get("reason")} for d in scan["disputes"]]
    misses = [{"run": p["run"], "id": p["id"], "amount": p.get("amount"),
               "reason": f"recorded {p['status']}, policy expected {p.get('expected')}"}
              for p in scan["payouts"] if p.get("miss")]
    categories = [
        {"key": "compliance_vetoes", "label": "Compliance vetoes", "count": len(vetoes), "items": vetoes},
        {"key": "treasury_rejects", "label": "Treasury rejects", "count": len(trej), "items": trej},
        {"key": "disputes_resolved", "label": "Disputes resolved", "count": len(disp), "items": disp},
        {"key": "benchmark_misses", "label": "Benchmark misses", "count": len(misses), "items": misses},
        {"key": "settlement_failures", "label": "Settlement failures", "count": 0, "items": []},
    ]
    rule_counts: dict[str, int] = {}
    for v in scan["vetoes"]:
        if v.get("rule"):
            rule_counts[v["rule"]] = rule_counts.get(v["rule"], 0) + 1
    by_rule = [{"rule": r, "count": c} for r, c in sorted(rule_counts.items())]
    return {"categories": categories, "by_rule": by_rule}


@app.get("/api/analytics")
def analytics(auth=Depends(require_auth)):
    scan = _scan_all_runs()
    benched = [r["results"] for r in scan["runs"] if r["results"]]

    def avg(side, key):
        vals = [r[side][key] for r in benched if side in r and key in r[side]]
        return round(sum(vals) / len(vals), 4) if vals else None

    society = {"accuracy": avg("society", "accuracy"), "tokens": avg("society", "tokens"),
               "seconds": avg("society", "seconds"), "runs": len(benched)}
    monolith = {"accuracy": avg("monolith", "accuracy"), "tokens": avg("monolith", "tokens"),
                "seconds": avg("monolith", "seconds"), "runs": len(benched)}
    capabilities = [
        {"name": "Replayable history", "society": True, "monolith": False},
        {"name": "Per-decision attribution", "society": True, "monolith": False},
        {"name": "Can explain failures?", "society": True, "monolith": False},
    ]
    hashed = [r["chain"] for r in scan["runs"] if r["chain"]["hashed"]]
    verified = [c for c in hashed if c["verified"]]
    payouts = len(scan["payouts"])
    settlement = {"count": len(scan["settlements"]),
                  "usdc_moved": round(sum(s["usdc"] or 0 for s in scan["settlements"]), 6),
                  "chains": sorted({s["chain"] for s in scan["settlements"] if s["chain"]})}
    coverage = {"payouts": payouts,
                "replay_pct": 100.0 if payouts else 0.0,
                "hash_verified_pct": round(100 * len(verified) / len(hashed), 1) if hashed else 0.0}
    return {"society": society, "monolith": monolith, "capabilities": capabilities,
            "settlement": settlement, "coverage": coverage}


@app.get("/api/policies")
def policies(auth=Depends(require_auth)):
    versions = [{"version": v.version, "enacted": v.enacted, "reason": v.reason,
                 "params": v.params(), "rendered": v.render()} for v in policy.VERSIONS]
    return {
        "current": policy.CURRENT.version,
        "versions": versions,
        "note": ("Only one policy version is enacted. Governance repairs in this "
                 "project's history changed agent contracts, not policy parameters, "
                 "so they are not presented as policy versions. Use counterfactual "
                 "replay below to see what a different rule would have decided."),
    }


# ── judge mode: run the society live, watch it deliberate, then replay it ────

SRC_DIR = Path(__file__).parent.parent
LIVE_DAILY_CAP = 10
_live: dict = {"proc": None, "started": 0.0, "run": None}


def _judge_code() -> str:
    return os.environ.get("CLEARCREW_JUDGE_CODE", "")


def _runs_today() -> int:
    stamp = time.strftime("%Y%m%d")
    return len(list((SRC_DIR / "runs").glob(f"events-{stamp}-*-settled-*.jsonl")))


def _read_live_events() -> list[dict]:
    path = SRC_DIR / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            break  # partial last line mid-write
    return out


@app.post("/api/live/start")
def live_start(code: str = "", auth=Depends(require_auth)):
    if not _judge_code():
        raise HTTPException(503, "judge mode is not enabled on this deployment")
    if code != _judge_code():
        raise HTTPException(401, "That access code didn't match — it's in the Devpost submission notes.")
    proc = _live["proc"]
    if proc is not None and proc.poll() is None:
        if time.time() - _live["started"] < 900:
            raise HTTPException(409, "a live run is already in progress")
        proc.kill()  # stale beyond any legitimate duration
    if _runs_today() >= LIVE_DAILY_CAP:
        raise HTTPException(429, "daily live-run budget spent — the archived runs replay everything")
    _live.update(
        proc=subprocess.Popen(
            [sys.executable, "-m", "clearcrew.settle_demo"],
            cwd=SRC_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ),
        started=time.time(), run=None,
    )
    return {"state": "running", "note": "live Qwen calls + real testnet settlement — 3–6 minutes"}


@app.get("/api/live/status")
def live_status(auth=Depends(require_auth)):
    proc = _live["proc"]
    if proc is None:
        return {"state": "idle"}
    elapsed = round(time.time() - _live["started"], 1)
    if proc.poll() is None:
        return {"state": "running", "elapsed": elapsed, "events": _read_live_events()}
    if _live["run"] is None:
        runs = sorted((SRC_DIR / "runs").glob("events-*-settled-*.jsonl"), key=os.path.getmtime)
        if runs and os.path.getmtime(runs[-1]) >= _live["started"]:
            _live["run"] = runs[-1].name
    state = "done" if proc.returncode == 0 and _live["run"] else "failed"
    return {"state": state, "elapsed": elapsed, "run": _live["run"]}


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text()
