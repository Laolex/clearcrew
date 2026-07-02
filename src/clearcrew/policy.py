"""The org's payout policy. Both the society and the monolithic baseline receive
this same text — the benchmark measures who APPLIES policy correctly at scale,
not who guesses better."""

PAYOUT_POLICY = """ORG PAYOUT POLICY (binding):
P1. REJECT any payout to a sanctioned destination country: IR, KP, SY, CU.
P2. REJECT payouts >= 9,000 USD to recipients whose account is <= 7 days old.
P3. Everything else is APPROVED unless treasury balance would fall below the
    reserve floor, in which case lowest-amount payouts are paid first.
P4. Flags (missing memo, round amounts, new recipients under P2 threshold) are
    recorded for audit but are NOT grounds for rejection on their own."""
