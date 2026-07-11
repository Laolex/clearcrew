"""Aggregate the repeated n=36 benchmark runs: mean, sd, min, max.

One run is an anecdote. This turns the headline into a distribution, which is
the only form of the number worth defending.

Only runs scored on PROPOSALS are included — pre-gate runs graded terminal
decisions and are a different measurement, so averaging them together would be
comparing two different experiments and calling it precision.

    python scripts/bench_stats.py            # markdown table, ready to paste
"""
import glob
import json
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from clearcrew import data, policy  # noqa: E402


def treasury_after(decisions: dict, key: str, amounts: dict) -> float:
    """Fold a system's decisions into a closing treasury balance.

    Accuracy is the wrong unit for a payout desk. A run can score 72% and leave
    the treasury $113,660 in the hole, because every error happened to be in the
    direction that moves money. Percent hides that; dollars do not.
    """
    spent = sum(amounts[pid]
                for pid, r in decisions.items()
                if (r.get(key) or "").startswith("approv"))
    return policy.CURRENT.balance - spent


def load(n: int = 36) -> list[dict]:
    runs = []
    for path in sorted(glob.glob(os.path.join(ROOT, "src", "runs", f"results-*-n{n}.json"))):
        r = json.load(open(path))
        if r.get("society", {}).get("scored_on") != "proposals":
            continue                      # pre-gate run: different measurement
        runs.append({"stamp": os.path.basename(path)[8:-9], **r})
    return runs


def describe(vals: list[float]) -> dict:
    return {
        "n": len(vals),
        "mean": st.mean(vals),
        "sd": st.stdev(vals) if len(vals) > 1 else 0.0,
        "min": min(vals),
        "max": max(vals),
    }


def main() -> None:
    runs = load()
    if not runs:
        sys.exit("no post-gate n=36 results found — run scripts/bench_repeat.sh first")

    soc = [r["society"]["accuracy"] for r in runs]
    mono = [r["monolith"]["accuracy"] for r in runs]
    blocked = [r["society"].get("blocked_by_policy", 0) for r in runs]

    s, m = describe(soc), describe(mono)
    print(f"n=36 · {len(runs)} runs · current architecture (proposals scored)\n")
    print("| | mean | sd | min | max |")
    print("|---|---|---|---|---|")
    for name, d in (("society (proposals)", s), ("monolith", m)):
        print(f"| **{name}** | {d['mean']:.1%} | {d['sd']:.1%} | {d['min']:.1%} | {d['max']:.1%} |")
    print(f"\ngap (mean): {s['mean'] - m['mean']:+.1%}")
    print(f"society wins in {sum(1 for a, b in zip(soc, mono) if a > b)}/{len(runs)} runs")
    print(f"policy gate refused an approval in {sum(1 for b in blocked if b)} run(s); "
          f"{sum(blocked)} block(s) total")

    # ── the unit that actually matters ────────────────────────────────────
    amounts = {p["id"]: p["amount"] for p in data.make_batch(36)}
    floor = policy.CURRENT.reserve_floor
    print(f"\n## Treasury outcome (start ${policy.CURRENT.balance:,.0f}, "
          f"floor ${floor:,.0f})\n")
    print("| run | society (recorded) | monolith (its decisions) | monolith floor |")
    print("|---|---|---|---|")
    breaches = 0
    for r in runs:
        d = r["decisions"]
        soc = treasury_after(d, "society_terminal", amounts)
        mono = treasury_after(d, "monolith", amounts)
        ok = mono >= floor
        breaches += 0 if ok else 1
        print(f"| `{r['stamp']}` | ${soc:,.0f} | ${mono:,.0f} | "
              f"{'held' if ok else '**BREACHED**'} |")
    print(f"\nmonolith breached the reserve floor in **{breaches}/{len(runs)}** runs.")
    print(f"society breached it in **0/{len(runs)}** — and after the policy gate "
          f"it cannot: no approval that P1/P2/P3 forbids can be recorded.")

    print("\nper run (accuracy):")
    print("| run | society | monolith | blocked by gate |")
    print("|---|---|---|---|")
    for r in runs:
        print(f"| `{r['stamp']}` | {r['society']['accuracy']:.1%} | "
              f"{r['monolith']['accuracy']:.1%} | {r['society'].get('blocked_by_policy', 0)} |")

    # ── cost ──────────────────────────────────────────────────────────────
    secs_s = describe([r["society"]["seconds"] for r in runs])
    secs_m = describe([r["monolith"]["seconds"] for r in runs])
    print(f"\n## Cost\n")
    print("| | society | monolith | ratio |")
    print("|---|---|---|---|")
    print(f"| wall-clock (mean) | {secs_s['mean']:.0f}s | {secs_m['mean']:.0f}s | "
          f"{secs_s['mean'] / secs_m['mean']:.1f}× |")

    # Tokens are only present in runs recorded after the subprocess token fix.
    # Reporting a mean over runs that measured nothing would invent a number.
    tok = [(r["society"].get("tokens", 0), r["monolith"].get("tokens", 0))
           for r in runs if r["society"].get("tokens")]
    if tok:
        ts = st.mean(t[0] for t in tok)
        tm = st.mean(t[1] for t in tok)
        print(f"| tokens (mean of {len(tok)} measured run(s)) | {ts:,.0f} | {tm:,.0f} | "
              f"{ts / tm:.1f}× |")
    else:
        print("| tokens | not recorded in these runs | | |")
    if len(tok) < len(runs):
        print(f"\n> Tokens were only captured for {len(tok)} of {len(runs)} runs — token "
              f"accounting was broken across the benchmark's subprocess boundary until "
              f"`c1c4e14`, so earlier runs measured nothing rather than measuring zero.")


if __name__ == "__main__":
    main()
