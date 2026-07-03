# Demo material — the self-caught error (n=36 run, 2026-07-02)

At batch size 36, society and monolith both scored 97% — one error each, on
different payouts. The difference: the society's error is fully diagnosable from
the event log, and was **flagged as incorrect by the society's own Auditor**.
The monolith's error (rejected 6bf46c69, a legitimate $5,000 GB→NG payout) has
no trail at all.

## The society's error: payout 5affb229 ($5,000 US→PH, 2-day-old recipient, expected: approve)

Recovered event chain (payloads truncated at 300 chars; original log was
overwritten before archiving was added — bench now archives every run to `runs/`):

1. **intake.classified** (intake): risk_tier "high" — "Recipient account is 2 days
   old (<= 7 days) and amount is 5000.0 USD (< 9000 USD). While P2 threshold is
   not met for automatic rejection, the combination ... triggers high risk scrutiny"
2. **compliance.reviewed** (compliance): verdict **clear** — "does not violate P1
   (PH is not a sanctioned country) or P2 (amount is 5,000 USD, which is below the
   9,000 USD threshold). The flag ... is noted for audit per P4 but is not grounds
   for rejection." ← CORRECT
3. **treasury.decided** (treasury): action **reject** — "P2 violation: amount >=
   9000 USD and recipient age <= 7 days (2 days)." ← WRONG on both facts: $5,000
   is not >= $9,000, and P2 is not treasury's rule to apply
4. **payout.rejected** (orchestrator)
5. **audit.explained** (auditor): "...Treasury ultimately rejected the transaction
   due to an **incorrect determination** that the amount violated the P2 policy
   limit." ← the system caught its own error, unprompted, in plain English

## Why this is the demo

- Monolith: one silent error, no trail, no attribution, no way to ask why.
- Society: one error — located to a specific agent, with the wrong reasoning on
  the record, contradicted by the compliance event above it, and called out by
  the audit layer automatically.

## The fix it produced (real governance, not prompt-tweaking)

Separation of duties: Treasury was re-litigating compliance rules. Its prompt now
forbids re-evaluating P1/P2 — cleared payouts are cleared; treasury only applies
P3 (reserve floor / funding order). This mirrors how real back offices prevent
exactly this class of error, and the audit trail is what surfaced the need for it.

## Act 2 — the benchmark itself was wrong, and the trail caught that too

After the separation-of-duties fix, the society appeared to DROP to 94% while the
monolith held 97%. Reading the trail: the society's two "misses" were the two
$15,000 payouts, rejected by Treasury for the reserve floor. Check the math —
policy-clean payouts totaled $114,460 against $90,000 available above the floor.
Rejecting exactly those two is the OPTIMAL application of P3 (no single cut
suffices: $99,460 still over). The society was 36/36; the ground-truth labels
only modeled P1/P2 and were scoring correct treasury behavior as errors — while
rewarding the monolith for silently approving a $24,460 overdraw as "97%".

## Final result (labels now model the full policy, run archived
`runs/events-20260702-152154-n36.jsonl`)

| batch | society | monolith |
|---|---|---|
| n=12 | 100% | 100% |
| n=36 | **100%** | **89%** |

Monolith's four n=36 errors, both failure directions:
- approved 62c33a4f + dbf4a8b2 ($15k each) → breaches the treasury reserve floor
- rejected 6bf46c69 + 5affb229 (clean $5k payouts) → recipients unpaid, no reason
  retrievable

## Act 3 — "but wait — … Reject." (action: pay_now)

With hash chaining live, a fresh n=36 run scored 94%: Treasury, asked to do the
funding waterfall as mental arithmetic across 24 payouts, collapsed into
per-payout boilerplate ("Cleared payout; sufficient treasury balance") and
breached the reserve floor. Fix: **agents judge, ledgers add** — the orchestrator
computes the cumulative ledger deterministically and hands it to Treasury AND to
the monolith (fairness).

Next run, 97% — and the single miss is the best artifact in the repo. Treasury's
recorded decision for 62c33a4f, verbatim (`runs/events-20260702-205623-n36.jsonl`):

> reason: "Cumulative total 99460.0 > headroom 90000.0, but wait — 84460 + 15000
> = 99460 > 90000. **Reject.**"
> action: **"pay_now"**

The model's own reasoning concluded Reject; its structured action said pay_now.
The trail didn't just explain the error — it showed the error was detectable at
decision time. Fix: **code flags, agents rule** — P3 over a computed ledger is
arithmetic, so the orchestrator reconciles every treasury action against the
ledger; mismatches become recorded `reconciliation.flagged` disputes ruled on by
Resolution.

Final run (`runs/events-20260702-210640-n36.jsonl`): society **100%**, monolith
89%, hash chain verified across all 179 events. The reconciliation guard was
armed and did not need to fire — Treasury, with the ledger, got it right.

## Video beat sequence

Slide asset: `docs/accountable-failure.png` — opaque-vs-accountable failure,
real payout 5affb229 on both sides. Use it as the bridge between beats 3 and 4.

1. Benchmark table n=12: 100% vs 100%. "At toy scale, everyone looks trustworthy."
2. n=36: 100% vs 89%. "At real batch sizes the single agent fails silently in
   both directions — it overdraws your treasury AND strands clean payouts."
3. Monolith's mistake: show the decision. "We tried to replay the monolith's
   decision. We couldn't. It never recorded why it chose what it chose — the
   verdict was printed and discarded. That absence IS the problem." (True
   story: until commit d2d747f the bench didn't even archive monolith
   verdicts — only the society left anything behind to archive.)
4. The society's earlier error: step through the 5-event trail. Land on the
   auditor line catching Treasury's hallucination in-band.
5. "The trail didn't just explain the error — it told us which agent to fix
   (separation of duties) and then caught our own benchmark mislabeling correct
   treasury behavior. History isn't a log. It's how the system gets better."
6. The "but wait" screenshot: Treasury's reason ends "Reject." — its action says
   pay_now. "The contradiction was sitting in the event, machine-checkable. Now
   the orchestrator checks: code flags, agents rule."
7. Replay Time Machine walkthrough on the final verified run: green ⛓ chain
   badge, step to the end of a chain, land on the assertions —
   "✓ reconstructed · ✓ chain verified · ✓ matches policy". Nothing staged.
8. Closer — counterfactual replay (`docs/counterfactual-replay.png`): open the
   ⑂ panel on the verified run, set reserve floor to 40,000, click Replay.
   Three $9,800 payouts flip approve→reject, rule P3, recorded outcomes
   untouched. "History here isn't just a record — it's executable. What would
   this batch have done under next quarter's policy? That's not prediction.
   That's arithmetic over history." End card.
