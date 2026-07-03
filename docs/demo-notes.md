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

## SHOOT LIST — exactly what to record (~3:00 total)

Setup once: 1920×1080 display, browser at 100% zoom, bookmarks bar hidden,
one tab, record https://clearcrew.verasettle.com (the LIVE deploy — judges may
recognize the URL). Move the cursor slowly; every click below is deliberate.
Record screen+voice in one take per shot; stitch after.

| # | time | on screen | you do | you say (gist) |
|---|---|---|---|---|
| 1 | 0:00–0:15 | `docs/thumbnail.png` full-screen | nothing | "ClearCrew: five Qwen agents run payout operations. Agents decide, history verifies, money moves. All three are real — here's the proof." |
| 2 | 0:15–0:35 | README **headline run** table (scroll to it on GitHub) | hover the 100% and 89% rows | "Same batch, same policy, same models. At n=12 everyone's perfect. At n=36 the single agent silently overdraws the treasury AND strands clean payouts — 89%. The society: 100%." |
| 3 | 0:35–1:00 | `docs/accountable-failure.png` full-screen | pause on left panel, then right | "Both systems once wrongly rejected this same $5,000 payout. We tried to replay the monolith's decision — we couldn't; it never recorded why. The society's failure came with a name, a rule, and a fix. Failure that can be explained is failure that can be repaired." |
| 4 | 1:00–1:30 | live site → deep link `#events-20260702-152154-n36.jsonl/5affb229` | step with → key through all 5 events, land on the green auditor card | "Watch the recorded trail: compliance clears it, Treasury hallucinates a violation — and the society's own Auditor catches the error in-band, unprompted. That told us which agent to fix." |
| 5 | 1:30–1:50 | deep link `#events-20260702-205623-n36.jsonl/62c33a4f` | step to Treasury's event, hover the reason text | "Best artifact in the repo. Treasury's reasoning ends 'Reject.' Its action field says pay_now. Machine-checkable contradiction — so now code flags, agents rule: every treasury action is reconciled against the ledger." |
| 6 | 1:50–2:10 | deep link `#events-20260702-210640-n36.jsonl` (headline run) | point at green ⛓ badge; open any payout, press Play, let it run to the assertions | "Final run: 100 percent, hash chain verified across 179 events. Every replay ends with these three checks — reconstructed, verified, matches policy. Nothing on this screen is staged." |
| 7 | 2:10–2:30 | same run, ⑂ counterfactual panel | type 40000 in reserve floor, click Replay, point at the 3 flips | "History is executable. Fold the same recorded batch through next quarter's policy: three payouts flip, rule P3, recorded outcomes untouched. Not prediction — arithmetic over history." |
| 8 | 2:30–2:55 | deep link `#events-20260703-165045-settled-n6.jsonl/1818e811` | step to the teal VERASETTLE event, **click the tx link**, let Basescan load | "And verdicts move money. This $9,800 approval executed as real testnet USDC through Verasettle — the tx hash is on Base Sepolia, the receipt lives in the same tamper-evident chain as the reasoning that caused it. Decision to movement, one verifiable history." |
| 9 | 2:55–3:00 | back to the UI on **SETTLED ON-CHAIN** state bar | nothing | "ClearCrew — clearcrew.verasettle.com. Nothing staged." (end card: repo URL) |

Highlight priorities if trimming: shots 2, 5, 8 are the ones judges must see
(the number, the contradiction, the money). Shot 4 is the emotional core.
Cut 7 first, then 3, never 8.

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
8. Counterfactual replay (`docs/counterfactual-replay.png`): open the
   ⑂ panel on the verified run, set reserve floor to 40,000, click Replay.
   Three $9,800 payouts flip approve→reject, rule P3, recorded outcomes
   untouched. "History here isn't just a record — it's executable. What would
   this batch have done under next quarter's policy? That's not prediction.
   That's arithmetic over history."
9. CLOSER — real money moves (`docs/settled-on-chain.png`, run
   `events-20260703-165045-settled-n6.jsonl`, deep link `/1818e811`): step the
   $9,800 payout to the end. Intake → fast-track → treasury ledger →
   approved → auditor → settlement.requested → VERASETTLE
   settlement.confirmed with a real Base Sepolia tx hash → SETTLED ON-CHAIN.
   "These aren't simulated payouts. The society's verdicts execute as real
   testnet USDC through Verasettle — and the settlement receipt lives in the
   same tamper-evident history as the reasoning that caused it. Decision to
   movement, one verifiable chain." Click the tx link to Basescan. End card.
