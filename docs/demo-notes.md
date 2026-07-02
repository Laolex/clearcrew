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

## Video beat sequence

1. Show benchmark table: 97% vs 97%. "Both made one mistake."
2. Monolith's mistake: show the decision. "Why? There is no why."
3. Society's mistake: step through the 5 events above. Land on the auditor line.
4. "The system that keeps history doesn't just explain its errors — it catches
   them, and tells you which agent to fix."
5. Show the separation-of-duties fix + the post-fix run.
