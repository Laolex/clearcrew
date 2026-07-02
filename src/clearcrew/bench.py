"""Benchmark: agent society vs single monolithic agent on the same labeled batch.

Usage: DASHSCOPE_API_KEY=... python -m clearcrew.bench
"""
import copy
import os
import time

from . import baseline, config, data, events, llm, orchestrator


def score(decisions: dict[str, str], batch: list[dict]) -> float:
    correct = sum(1 for p in batch if decisions.get(p["id"], "?").startswith(p["_expected"][:6]))
    return correct / len(batch)


def run() -> None:
    batch = data.make_batch(n=int(os.environ.get("BATCH_N", "12")))
    clean = [{k: v for k, v in p.items() if k != "_expected"} for p in batch]

    # --- society ---
    config.EVENT_LOG_PATH = "events.jsonl"
    if os.path.exists(config.EVENT_LOG_PATH):
        os.remove(config.EVENT_LOG_PATH)
    llm.usage_totals.update(prompt_tokens=0, completion_tokens=0, calls=0)
    t0 = time.time()
    result = orchestrator.run_batch(copy.deepcopy(clean))
    society_decisions = {pid: s["status"] for pid, s in result["state"].items() if pid != "batch"}
    society = {
        "seconds": round(time.time() - t0, 1),
        "tokens": llm.usage_totals["prompt_tokens"] + llm.usage_totals["completion_tokens"],
        "accuracy": score(society_decisions, batch),
        "auditable": True,
    }

    # --- monolith ---
    llm.usage_totals.update(prompt_tokens=0, completion_tokens=0, calls=0)
    t0 = time.time()
    mono_result = baseline.run_batch(copy.deepcopy(clean))
    mono_decisions = {d["payout_id"]: ("approved" if d["action"] == "approve" else "rejected")
                      for d in mono_result.get("decisions", [])}
    monolith = {
        "seconds": round(time.time() - t0, 1),
        "tokens": llm.usage_totals["prompt_tokens"] + llm.usage_totals["completion_tokens"],
        "accuracy": score(mono_decisions, batch),
        "auditable": False,
    }

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
        print(f"{name:<12}{r['accuracy']:>10.0%}{r['tokens']:>10}{r['seconds']:>10}{str(r['auditable']):>11}")


if __name__ == "__main__":
    run()
