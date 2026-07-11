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

Final run of that ladder (`runs/events-20260702-210640-n36.jsonl`): society
**100%**, monolith 89%, hash chain verified across all 179 events. The
reconciliation guard was armed and did not need to fire.

## Act 4 — ten runs, and the number we were reporting was the wrong one

One run is an anecdote, so we ran the final architecture ten times
(`scripts/bench_repeat.sh 10`).

| | mean | sd | min | max |
|---|---|---|---|---|
| society (proposals) | **100.0%** | 0.0% | 100.0% | 100.0% |
| monolith | 87.5% | 5.4% | **72.2%** | 91.7% |

Then we folded each system's own decisions into the treasury — and the accuracy
column turned out to have been hiding the result:

| | society | monolith |
|---|---|---|
| closing balance | **+$15,540**, every run | **negative, every run** |
| worst run | +$15,540 | **−$113,660** |
| reserve floor breached | **0 / 10** | **10 / 10** |

The single agent overdraws the treasury in **every run it has ever been given**.
And its *best* accuracy run (91.7%) closed at **−$9,460** — worse than four of
its 88.9% runs. **Accuracy went up while the outcome got worse**, because which
payouts you get wrong matters more than how many.

Its failure is structural, not noisy: the same four payouts, every stable run.
It approves *both* $15,000 P3 payouts — the reserve floor being the one rule that
cannot be judged one payout at a time — and rejects two clean $5,000 payouts by
over-applying P2 (which only bites at ≥ $9,000). A single agent reasoning locally
is blind to the only globally-scoped rule.

## Act 5 — the fix: agents propose, policy promotes

Grading after the fact tells you that you lost the money. So the policy layer
stopped grading and started **gating**: agents emit `payout.proposed`, and only
`orchestrator._promote()` can turn that into a terminal decision — and it may
only ever **refuse**. An approval that P1/P2/P3 forbids is recorded as
`policy.blocked` and the payout is rejected.

The reserve floor is therefore an **invariant, not a benchmark result**. The run
that overdrew by $24,460 is no longer expressible.

**Say this plainly on camera:** in all ten benchmark runs the gate blocked
*nothing*, because the agents proposed correctly every time. That is not a
weakness — a seatbelt that never deploys is still doing its job — but claiming it
fires would be exactly the dishonesty this project exists to kill. Show the
adversarial test instead (`test_reserve_floor_is_an_invariant_not_a_grade`): a
society that proposes to approve *everything*, and the floor holds anyway.

## Act 6 — and the chain is now anchored outside itself

A hash chain is computed by the process that writes the log, so anyone who can
rewrite the file can rewrite the hashes and verify clean. Hash chaining alone is
tamper-*evident*, not tamper-*proof* — and we used to blur that.

Now every run's head hash is signed by an independent RFC-3161 Time Stamping
Authority (`chain.anchored`). To rewrite an anchored run you would have to forge
freetsa.org's signature. All 11 post-gate runs carry a token that verifies
against their own recorded head — and you can check it with `openssl`, not with
our code.

## SHOOT LIST — exactly what to record (~3:30 total)

Setup once: 1920×1080 display, browser at 100% zoom, bookmarks bar hidden,
one tab, record https://clearcrew.verasettle.com (the LIVE deploy — judges may
recognize the URL). Move the cursor slowly; every click below is deliberate.
Record screen+voice in one take per shot; stitch after.

| # | time | on screen | you do | you say (gist) |
|---|---|---|---|---|
| 1 | 0:00–0:15 | `docs/thumbnail.png` full-screen | nothing | "ClearCrew: five Qwen agents run payout operations. Agents decide, history verifies, money moves. All three are real — here's the proof." |
| 2 | 0:15–0:40 | README ten-run table + treasury table | hover the monolith's **91.7%** row, then its **−$9,460** | "Same batch, same policy, same models, ten runs. But look at this: the single agent's BEST run lost the most money. Accuracy went up, the outcome got worse. So we stopped counting percentages." |
| 3 | 0:40–1:05 | README treasury table | hover **10 / 10 breached** and **−$113,660** | "Folded into the treasury: the single agent overdraws in ten runs out of ten. Once by more than the entire opening balance. The society: zero out of ten." |
| 4 | 1:05–1:35 | live site → Operations → **eval bar** | click *fold the batch*, let the bar drain and hold above the red floor line | "This is the treasury falling as each recorded decision lands. Watch it stop — floor held, fifteen thousand five hundred and forty left." |
| 5 | 1:35–2:00 | switch run to `events-20260702-204555-n36.jsonl`, fold again | let the bar drain straight THROUGH the floor and turn red | "Now one of our own early runs. Straight through the floor — fourteen thousand overdrawn. We publish it. And the record says exactly why: Treasury judged each payout alone and never wrote down a running total." |
| 6 | 2:00–2:20 | payout detail on a blocked payout (or the adversarial test in a terminal) | point at *Society proposed: approve → Policy gate: REFUSED — P1 → Decision: REJECTED* | "So agents stopped deciding. They propose. A deterministic gate promotes — or refuses, and the refusal goes on the record in the agent's own words. It can only ever refuse: if it could approve, the agents would be decorative." |
| 7 | 2:20–2:35 | terminal: `pytest -k reserve_floor` | let it pass | "Here's a society that proposes to approve everything. The floor holds anyway. The reserve floor stopped being a score and became an invariant." |
| 8 | 2:35–2:55 | deep link `#events-20260702-205623-n36.jsonl/62c33a4f` | step to Treasury's event, hover the reason text | "Best artifact in the repo. Treasury's reasoning ends 'Reject.' Its action field says pay_now. A machine-checkable contradiction, sitting in the record." |
| 9 | 2:55–3:15 | a `chain.anchored` event, then terminal `openssl ts -verify …` → **Verification: OK** | let openssl print OK | "One more thing about that chain — we write it, so we could rewrite it. So we don't only trust ourselves: an independent authority signs our head hash with its own key. That's openssl checking it, not our code." |
| 10 | 3:15–3:35 | deep link `#events-20260703-165045-settled-n6.jsonl/1818e811` | step to the teal VERASETTLE event, **click the tx link**, let Basescan load | "And verdicts move money. This $9,800 approval executed as real testnet USDC — the receipt lives in the same tamper-evident chain as the reasoning that caused it." |
| 11 | 3:35–3:40 | back to the UI on **SETTLED ON-CHAIN** state bar | nothing | "ClearCrew — clearcrew.verasettle.com. Nothing staged." (end card: repo URL) |

Highlight priorities if trimming: **shots 2, 4, 5 are the video** — the wrong
unit, the floor holding, the floor breaking. Then 9 (the anchor) and 10 (the
money). Cut 8 first, then 7, never 5.

## Video beat sequence

1. **The wrong unit.** Ten runs. The monolith's best accuracy run lost the most
   money. "Accuracy went up. The outcome got worse."
2. **The money.** Fold the decisions into the treasury: monolith overdraws
   10/10, worst run −$113,660 — more than the whole opening balance. Society
   0/10.
3. **Why.** It approves BOTH P3 payouts and strands two clean $5,000s, the same
   four every run. The reserve floor is the one rule you cannot check one payout
   at a time. No single payout breaches it — the twenty-fourth one does.
4. **The eval bar.** Fold the batch and watch the treasury fall. Society holds at
   $15,540. Then run `20260702-204555` — one of OURS — and watch it go through
   the floor to −$14,460. We publish our losses.
5. **The trail repairs it.** Treasury said "sufficient balance" 24 times, each
   time correctly, about one payout. The record didn't just explain the failure,
   it prescribed the fix.
6. **The gate.** Agents propose; policy promotes; the gate can only refuse. The
   reserve floor becomes an invariant — the overdrawing run is no longer
   expressible. (Be honest: in ten runs it blocked nothing. Show the adversarial
   test instead.)
7. **The anchor.** We write the chain, so we could rewrite it. An independent
   RFC-3161 authority signs the head hash. Verify with `openssl`, not our code.
8. **The money moves.** Real testnet USDC on Base Sepolia; receipt in the same
   chain as the reasoning. Click through to Basescan.
9. **Close.** "The single agent overdrew the treasury in ten runs out of ten, and
   could not tell you why. ClearCrew doesn't — and now, it can't."
