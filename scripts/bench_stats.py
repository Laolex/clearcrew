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

    print("\nper run:")
    print("| run | society | monolith | blocked |")
    print("|---|---|---|---|")
    for r in runs:
        print(f"| `{r['stamp']}` | {r['society']['accuracy']:.1%} | "
              f"{r['monolith']['accuracy']:.1%} | {r['society'].get('blocked_by_policy', 0)} |")


if __name__ == "__main__":
    main()
