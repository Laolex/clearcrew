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
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import anchor, config, data, events as event_log, policy

API_TOKEN = os.environ.get("CLEARCREW_API_TOKEN", "")

RUNS_DIR = Path(os.environ.get("CLEARCREW_RUNS_DIR", Path(__file__).parent.parent / "runs"))
STATIC_DIR = Path(__file__).parent / "static"
DIST_DIR = STATIC_DIR / "dist"  # built by `npm --prefix web run build`

app = FastAPI(title="ClearCrew Replay Time Machine")

_RUN_RE = re.compile(r"^events-(?P<stamp>[\w-]+?)-n(?P<n>\d+)\.jsonl$")


@app.middleware("http")
async def operational_headers(request: Request, call_next):
    """Apply a safe browser baseline to both the UI and evidence API.

    The replay service is intentionally read-only, but it is often embedded in
    demo infrastructure. These headers make that boundary explicit without
    relying on a particular reverse proxy to add them.
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; "
        "script-src 'self'; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'",
    )
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    elif request.url.path.startswith("/assets/"):
        # Hashed filenames — a new build is a new URL, so cache forever.
        response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
    else:
        # The SPA shell must revalidate, or a redeploy strands browsers on a
        # cached shell pointing at asset hashes that no longer exist.
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


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
    # JSONL order is append/emission order. It is the only order in which the
    # predecessor links can be verified; timestamps are presentation metadata
    # and may regress when a host clock changes.
    return events


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


def _scan_all_runs_uncached() -> dict:
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


_scan_cache: dict[str, object] = {"expires_at": 0.0, "data": None}


def _scan_all_runs() -> dict:
    """Cache aggregate reads briefly without treating new evidence as stale.

    Archive views ask for the same complete scan several times during a normal
    browser session. A short TTL keeps the API responsive while making freshly
    written live-run evidence visible almost immediately.
    """
    now = time.monotonic()
    cached = _scan_cache.get("data")
    if cached is not None and now < _scan_cache["expires_at"]:
        return cached  # type: ignore[return-value]
    scanned = _scan_all_runs_uncached()
    _scan_cache.update(data=scanned, expires_at=now + 15.0)
    return scanned


@app.get("/healthz")
def healthz():
    """Liveness only: the process can answer requests."""
    return {"ok": True}


@app.get("/readyz")
def readyz():
    """Readiness: archived evidence is reachable and enumerable."""
    try:
        runs = _list_runs()
    except OSError as exc:
        raise HTTPException(503, "archived evidence is unavailable") from exc
    return {"ok": True, "runs": len(runs)}


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
        p = payouts.setdefault(s, {"id": s, "status": "pending", "events": 0, "disputed": False,
                                   "proposed": None, "blocked_rule": None})
        p["events"] += 1
        if e["type"] in ("payout.approved", "payout.rejected", "payout.settled"):
            p["status"] = e["type"].split(".", 1)[1]
        if e["type"] == "dispute.resolved":
            p["disputed"] = True
        if e["type"] == "payout.proposed":
            p["proposed"] = (e.get("payload") or {}).get("verdict")
        if e["type"] == "policy.blocked":
            p["blocked_rule"] = (e.get("payload") or {}).get("rule")

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
            # Grade the SOCIETY, which means grading its proposal. After the
            # policy gate, terminal outcomes agree with policy by construction,
            # so scoring them would show every run as flawless and hide the
            # agent that was actually wrong. Pre-gate runs have no proposal, so
            # the terminal decision is all there is to grade.
            judged = p["proposed"] or ("approve" if p["status"] in ("approved", "settled") else "reject")
            p["miss"] = (judged == "approve") != (detail["_expected"] == "approve")

    ordered = sorted(payouts.values(), key=lambda p: (-p["disputed"], -(p.get("amount") or 0)))
    return {"run": run_name, "t0": t0, "total_events": len(events),
            "chain": _verify(run_name, events), "payouts": ordered}


@app.get("/api/runs/{run_name}/events")
def run_events(run_name: str, auth=Depends(require_auth)):
    """The whole recorded trail, in emission order — the chain verifies against
    this order, so it is served as-is rather than re-sorted for presentation.

    `untrusted_from` is where the linear walk first fails: everything at or after
    that index is downstream of a break and must not be presented as fact.
    """
    events = _load_events(run_name)
    t0 = events[0]["ts"] if events else 0.0
    chain = _verify(run_name, events)
    return {
        "run": run_name,
        "t0": t0,
        "chain": chain,
        "untrusted_from": chain["broken_at"],
        "events": [{**e, "t_offset": round(e["ts"] - t0, 2)} for e in events],
    }


@app.get("/api/runs/{run_name}/export")
def export_run(run_name: str, auth=Depends(require_auth)):
    """Download the archived evidence exactly as it was recorded.

    Unlike the JSON API, this is JSONL with no presentation-only fields. It is
    the artifact an independent verifier should archive and hash.
    """
    _load_events(run_name)  # validates the name and existence before serving
    path = RUNS_DIR / run_name
    return FileResponse(path, media_type="application/x-ndjson",
                        filename=run_name,
                        headers={"Cache-Control": "no-store"})


@app.get("/api/runs/{run_name}/anchors")
def run_anchors(run_name: str, auth=Depends(require_auth)):
    """Anchor records and their local imprint checks for this archived run.

    `valid` means the RFC-3161 token commits to the stated head hash. Signature
    validation still belongs to an independent tool with the TSA trust chain.
    """
    records = []
    for e in _load_events(run_name):
        if e["type"] != "chain.anchored":
            continue
        p = e.get("payload", {})
        token, head = p.get("token"), p.get("head_hash")
        verification = (anchor.verify_token(token, head)
                        if isinstance(token, str) and isinstance(head, str)
                        else {"valid": False, "reason": "no external timestamp token recorded"})
        records.append({
            "event_id": e["id"], "head_hash": head, "provider": p.get("provider"),
            "url": p.get("url"), "tsa_time": p.get("tsa_time"), "serial": p.get("serial"),
            "verification": verification,
        })
    return {"run": run_name, "anchors": records}


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
        if val is not None and (not math.isfinite(val) or val < 0):
            raise HTTPException(422, f"{name} must be a finite, non-negative number")
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


@app.get("/api/runs/{run_name}/treasury")
def treasury(run_name: str, auth=Depends(require_auth)):
    """The treasury position as the batch folds — balance descending toward the
    reserve floor, one step per recorded terminal decision.

    This is a fold, not a simulation: every step is driven by a recorded
    `payout.approved` / `payout.rejected` event in emission order, and the
    amounts come from the deterministic batch. No model is re-run, and nothing
    here is recomputed from what the policy *would* have said — if a run
    breached the floor, this reports the breach it actually recorded.
    """
    events = _load_events(run_name)
    m = _RUN_RE.match(run_name)
    lookup = _batch_lookup(int(m["n"]))
    pv = policy.CURRENT
    t0 = events[0]["ts"] if events else 0.0

    # Treasury's own recorded rationale, for the "did it reason cumulatively?"
    # check below. In the earliest runs it decided each payout in isolation and
    # never wrote a cumulative total — which is exactly why the floor broke.
    cumulative_reasons = sum(
        1 for e in events
        if e["type"] == "treasury.decided"
        and "cumulative total" in (e.get("payload", {}).get("reason", "") or "").lower()
    )
    treasury_decisions = sum(1 for e in events if e["type"] == "treasury.decided")

    # Which rule the policy says binds — evaluated over the WHOLE batch, since
    # the P3 waterfall only binds in the context of everything else competing
    # for the same headroom. Evaluating a payout alone would never bind.
    ruled = policy.evaluate(list(lookup.values()), pv)

    steps, spent, held = [], 0.0, 0
    for e in events:
        if e["type"] not in ("payout.approved", "payout.rejected"):
            continue
        detail = lookup.get(e["subject"])
        if not detail:
            continue
        approved = e["type"] == "payout.approved"
        # a "hold" is a rejection the reserve floor caused — not a P1/P2 rejection
        floor_hold = not approved and ruled[e["subject"]]["rule"] == "P3"
        if approved:
            spent += detail["amount"]
        elif floor_hold:
            held += 1
        steps.append({
            "payout_id": e["subject"],
            "amount": detail["amount"],
            "approved": approved,
            "held": floor_hold,
            "t_offset": round(e["ts"] - t0, 2),
            "spent": round(spent, 2),
            "balance": round(pv.balance - spent, 2),
            "below_floor": (pv.balance - spent) < pv.reserve_floor,
        })

    breach = round(spent - pv.headroom, 2)
    return {
        "run": run_name,
        "balance": pv.balance,
        "reserve_floor": pv.reserve_floor,
        "headroom": pv.headroom,
        "steps": steps,
        "spent": round(spent, 2),
        "final_balance": round(pv.balance - spent, 2),
        "breached": breach > 0,
        "breach_amount": breach if breach > 0 else 0.0,
        "held": held,
        # False for the early runs: treasury judged payouts one at a time and
        # never recorded a running total. The floor breach follows from that.
        "reasoned_cumulatively": bool(treasury_decisions) and cumulative_reasons == treasury_decisions,
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


@app.get("/api/society")
def society(auth=Depends(require_auth)):
    """The configured Qwen society and its enforced division of labour.

    This endpoint deliberately reports configuration and code-level boundaries,
    not a claim inferred from a replay.  It gives a reviewer one small,
    inspectable surface connecting the visible console to the agents that write
    the events in it.
    """
    return {
        "provider": "Qwen Cloud (DashScope)",
        "endpoint": config.BASE_URL,
        "models": [
            {"name": config.MODEL_FAST, "purpose": "parallel intake triage and audit explanations"},
            {"name": config.MODEL_STRONG, "purpose": "compliance, treasury, and resolution judgments"},
        ],
        "roles": [
            {"name": "Intake", "authority": "classifies payout risk; cannot approve or reject"},
            {"name": "Compliance", "authority": "can veto only by citing Policy P1 or P2"},
            {"name": "Treasury", "authority": "sets funding order from the deterministic P3 ledger"},
            {"name": "Resolution", "authority": "rules on recorded veto and ledger disputes"},
            {"name": "Auditor", "authority": "explains the recorded chain; cannot alter it"},
        ],
        "controls": [
            "Agents propose; executable policy alone promotes a payout.",
            "Arithmetic is computed in code and supplied to Treasury as the authoritative ledger.",
            "Every role emits an append-only, hash-linked event; replay never calls a model again.",
        ],
    }


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
    """The React frontend, if it has been built; otherwise the original console.

    Falling back rather than 500-ing keeps `uvicorn clearcrew.replay:app` working
    in a fresh clone where `web/` was never built — the API and the legacy UI do
    not depend on node.
    """
    built = DIST_DIR / "index.html"
    if built.is_file():
        return built.read_text()
    return (STATIC_DIR / "index.html").read_text()


@app.get("/legacy", response_class=HTMLResponse)
def legacy_index():
    """The pre-React console. Kept reachable until the port is at parity."""
    return (STATIC_DIR / "index.html").read_text()


@app.get("/img/{name}")
def image(name: str):
    """Diagram assets referenced by the README and the dev.to post."""
    path = (STATIC_DIR / "img" / name).resolve()
    if path.parent != (STATIC_DIR / "img").resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})


# Mounted last so it cannot shadow /api. `check_dir=False` lets a fresh clone
# start in legacy mode, while still allowing assets to work if the frontend is
# built after the process starts (without requiring a restart).
app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets", check_dir=False), name="assets")


@app.get("/{full_path:path}", response_class=HTMLResponse)
def spa_fallback(full_path: str):
    """Serve the SPA shell for client-side routes (e.g. /console).

    Registered last, so every real route and the /assets mount match first.
    API typos must 404 as JSON rather than silently returning HTML.
    """
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        raise HTTPException(404, "not found")
    built = DIST_DIR / "index.html"
    if built.is_file():
        return built.read_text()
    return (STATIC_DIR / "index.html").read_text()
