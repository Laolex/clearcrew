"""Ablation: how much of the treasury result is the SOCIETY, and how much is the GATE?

The README once put "society breached the floor 0/10" next to "monolith breached
it 10/10" without noting that only one of them had a policy gate. That comparison
credits the gate to the society, and it is not fair — the gate is
architecture-independent, and would protect a single agent just as well.

So: settle it with an experiment.

The gate is deterministic, so we do not need to re-run any model. We take each of
the ten RECORDED monolith decision sets and fold them through `policy.evaluate()`
exactly as `orchestrator._promote()` would — the same arithmetic-over-history the
counterfactual engine does. No model is re-run; nothing is simulated.

    python scripts/ablation.py
"""
import glob
import json
import os
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from clearcrew import data, policy  # noqa: E402


def gated(decisions: dict, key: str, ruled: dict) -> list[str]:
    """What the gate would let through. Veto-only: it can refuse an approval,
    never create one — so a rejection stays a rejection."""
    out = []
    for pid, r in decisions.items():
        proposed = (r.get(key) or "")
        wants_approve = proposed.startswith("approv")
        if wants_approve and ruled[pid]["verdict"] == "approve":
            out.append(pid)          # promoted
        # else: refused (policy.blocked) or proposed-reject -> not approved
    return out


def main() -> None:
    amounts = {p["id"]: p["amount"] for p in data.make_batch(36)}
    ruled = policy.evaluate(data.make_batch(36))
    floor, start = policy.CURRENT.reserve_floor, policy.CURRENT.balance

    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "src", "runs", "results-*-n36.json"))):
        r = json.load(open(path))
        if r.get("society", {}).get("scored_on") != "proposals":
            continue
        d = r["decisions"]

        mono_raw = [pid for pid, x in d.items() if (x.get("monolith") or "").startswith("approv")]
        mono_gated = gated(d, "monolith", ruled)
        soc = [pid for pid, x in d.items() if (x.get("society_terminal") or "").startswith("approv")]

        # Money that SHOULD have been paid and wasn't. The gate is veto-only, so
        # it cannot rescue a wrongly-rejected payout — a stranded payout stays
        # stranded no matter how good your governance is. Only judgment fixes it.
        def stranded(approved: list[str]) -> float:
            return sum(amounts[pid] for pid, v in ruled.items()
                       if v["verdict"] == "approve" and pid not in approved)

        rows.append({
            "stamp": os.path.basename(path)[8:-9],
            "mono_acc": r["monolith"]["accuracy"],
            "soc_acc": r["society"]["accuracy"],
            "mono_raw": start - sum(amounts[p] for p in mono_raw),
            "mono_gated": start - sum(amounts[p] for p in mono_gated),
            "soc": start - sum(amounts[p] for p in soc),
            "stranded_gated": stranded(mono_gated),
            "stranded_soc": stranded(soc),
            "blocked": sum(1 for pid, x in d.items()
                           if (x.get("monolith") or "").startswith("approv")
                           and ruled[pid]["verdict"] == "reject"),
        })

    if not rows:
        sys.exit("no post-gate n=36 results found")

    n = len(rows)
    print(f"# Ablation — {n} runs, n=36, start ${start:,.0f}, reserve floor ${floor:,.0f}\n")
    print("The gate is deterministic, so the monolith's RECORDED decisions are folded")
    print("through it. No model was re-run.\n")

    print("| run | monolith | monolith **+ gate** | society | blocked | **stranded** (mono+gate) |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(f"| `{r['stamp']}` | ${r['mono_raw']:,.0f} | ${r['mono_gated']:,.0f} | "
              f"${r['soc']:,.0f} | {r['blocked']} | ${r['stranded_gated']:,.0f} |")

    br_raw = sum(1 for r in rows if r["mono_raw"] < floor)
    br_gate = sum(1 for r in rows if r["mono_gated"] < floor)
    br_soc = sum(1 for r in rows if r["soc"] < floor)
    strand_g = st.mean(r["stranded_gated"] for r in rows)
    strand_s = st.mean(r["stranded_soc"] for r in rows)

    print(f"\n**Reserve floor breached:** monolith **{br_raw}/{n}** · "
          f"monolith+gate **{br_gate}/{n}** · society **{br_soc}/{n}**")
    print(f"**Legitimate payouts stranded (mean):** monolith+gate "
          f"**${strand_g:,.0f}** · society **${strand_s:,.0f}**")

    print("\n## What this settles\n")
    print(f"**1. The treasury protection is the GATE's, not the society's.** The gate")
    print(f"alone takes the single agent from **{br_raw}/{n} breaches to {br_gate}/{n}**.")
    print(f"It refused an average of **{st.mean(r['blocked'] for r in rows):.1f}** monolith")
    print(f"approvals per run — and **0** of the society's, because the society never")
    print(f"proposed one. Putting \"society 0/10\" beside \"monolith 10/10\" without saying")
    print(f"this would credit the society with the gate's work.\n")
    print(f"**2. But notice the gated monolith closes RICHER — ${rows[0]['mono_gated']:,.0f} vs the")
    print(f"society's ${rows[0]['soc']:,.0f} — and that is bad, not good.** A higher balance means")
    print(f"money that should have gone out didn't. The gate is veto-only by design: it")
    print(f"can refuse a payout that breaks the rules, but it can never *rescue* one that")
    print(f"was wrongly refused. The gated monolith holds the floor by not paying people")
    print(f"it owed — **${strand_g:,.0f} of legitimate payouts stranded, every run.**")
    print(f"The society strands **${strand_s:,.0f}**.\n")
    print(f"**3. So the two claims are cleanly separable:**\n")
    print(f"- **Governance stops you paying the wrong people.** Any architecture can have")
    print(f"  it; the monolith is welcome to it, and with it, it is safe.")
    print(f"- **Only judgment makes you pay the right ones.** No gate can fix a stranded")
    print(f"  payout. That is the society's real claim, and it is worth")
    print(f"  **${strand_g - strand_s:,.0f} per run** — plus the record explaining every call.")
    print(f"\nSociety vs monolith on judgment alone (proposals): "
          f"**{st.mean(r['soc_acc'] for r in rows):.1%}** vs "
          f"**{st.mean(r['mono_acc'] for r in rows):.1%}**.")


if __name__ == "__main__":
    main()
