# The night my AI agent caught another AI agent lying — building ClearCrew on Qwen Cloud

*Building an agent society for payout operations for the Qwen Cloud Global AI
Hackathon — and what the event log taught me that no eval score could.*

---

I entered the Agent Society track with a simple question: if you're going to let
AI move real money, is a *committee* of agents actually safer than one big smart
one? Not "feels safer" — measurably safer, on the same task, with the same
policy, same models, same batch.

So I built both and made them fight.

## The setup

**ClearCrew** runs payout operations as five Qwen agents with separated duties:

- **Intake** (qwen3.7-plus, thinking off) triages every payout into a risk tier.
  Low-risk payments fast-track — most never touch the expensive model.
- **Compliance** (qwen3.7-max) holds veto power, but a veto must cite a specific
  policy rule or it doesn't count.
- **Treasury** (qwen3.7-max) sequences funding under a reserve-floor waterfall.
- **Resolution** (qwen3.7-max) arbitrates: high-value vetoes trigger a recorded
  negotiation.
- **Auditor** (qwen3.7-plus) writes a plain-English explanation of every
  payout's full event chain.

The baseline is one monolithic qwen3.7-max prompt doing the whole job. Both get
the identical written org policy. Everything the society does is an event in an
append-only JSONL log — state is just a fold over events, and any decision can
be replayed.

All of it runs on Qwen Cloud's DashScope OpenAI-compatible endpoint, which made
the two-tier model strategy trivial: same client, swap the model string, use
`enable_thinking: false` on the fast tier.

## Round one: the committee lost

First benchmark, batch of 12: **society 58%, monolith 83%.** The committee was
slower, burned 10× the tokens, and was *wrong more often*. Compliance vetoed
half the batch on vibes — "unusual memo," "new-ish account" — because I hadn't
actually given anyone the policy. I'd built a bureaucracy, not a society.

The fix wasn't a better model. It was governance: one written policy given
identically to both systems, vetoes must cite a rule, and any payout without an
explicit final decision is rejected-by-default. Rerun: **100% vs 100%.** Fine.
At toy scale everyone looks trustworthy.

## Round two: the lie

Batch of 36. Society drops one payout — a clean $5,000 US→PH transfer,
wrongly rejected. And here's where the event log earned its keep. The trail for
payout `5affb229`, five events, verbatim:

1. **Intake:** risk tier *high* — new recipient account, worth scrutiny.
2. **Compliance:** *clear* — "amount is 5,000 USD, below the 9,000 USD
   threshold... noted for audit per P4 but not grounds for rejection." Correct.
3. **Treasury:** *reject* — "P2 violation: amount >= 9000 USD." **A $5,000
   payout.** Treasury hallucinated a compliance violation — a rule that wasn't
   even its job to apply — and overrode a correct clearance.
4. **Orchestrator:** payout rejected.
5. **Auditor:** "...Treasury ultimately rejected the transaction due to an
   **incorrect determination** that the amount violated the P2 policy limit."

Read that last line again. The system caught its own agent's error, unprompted,
in plain English, in the same run. The monolith made errors too that night —
but they were *silent*. No trail, no attribution, no way to ask why.

And the trail didn't just explain the failure — it prescribed the fix. Treasury
was re-litigating another agent's domain, which is exactly what separation of
duties exists to prevent in human back offices. One contract change ("you decide
funding order and ONLY funding order") and the class of error was gone.

## Round three: the benchmark itself was wrong

After the fix, the society *appeared* to regress: 94% vs the monolith's 97%. I
almost reverted. Then I read the trail. The society's two "misses" were two
$15,000 payouts rejected for the treasury reserve floor — and checking the
arithmetic, policy-clean payouts totaled $114,460 against $90,000 of available
balance. Rejecting exactly those two was the *optimal* application of the
funding waterfall. The society was 36/36. My ground-truth labels only modeled
the simple rules — they were punishing correct treasury behavior while rewarding
the monolith for silently approving a $24,460 overdraw and calling it "97%."

Fixed the labels to model the full policy. Final score:

| batch | society | monolith |
|---|---|---|
| n=12 | 100% | 100% |
| n=36 | **100%** | **89%** |

At real batch sizes the single agent fails in both directions: it overdraws the
treasury *and* strands clean payouts, with no recoverable explanation for
either. The society gets all 36 — including the two rejections that require
doing waterfall arithmetic across the entire batch.

## Round four: "but wait — … Reject." (action: pay_now)

After adding hash chaining to the event log (tamper-evident history — each event
commits to its predecessor), fresh runs surfaced two more failures, each caught
by reading the trail. First, Treasury — asked to do the funding waterfall as
mental arithmetic across 24 payouts — collapsed into per-payout boilerplate and
breached the reserve floor. Fix: *agents judge, ledgers add* — the cumulative
ledger is computed in code and handed to both systems. A judgment engine should
never be asked to be a calculator.

Then the best artifact in the repo. Treasury's recorded decision on a $15,000
payout, verbatim:

> reason: "Cumulative total 99460.0 > headroom 90000.0, but wait — 84460 + 15000
> = 99460 > 90000. **Reject.**"
> action: **"pay_now"**

Its own reasoning concluded Reject. Its structured action said pay_now. The
contradiction was sitting in the event, machine-checkable — so now the
orchestrator checks: every treasury action is reconciled against the ledger in
code, and mismatches become recorded disputes ruled on by the Resolution agent.
*Code flags, agents rule.* The final n=36 run: society 100%, monolith 89%, hash
chain verified across all 179 events.

## What I actually learned

1. **Agent societies don't win by default.** Ungoverned, mine lost badly. The
   wins came from the boring institutional stuff: written policy, cited rules,
   separation of duties, rejected-by-default.
2. **The audit trail is not a compliance checkbox — it's the debugging tool.**
   Every meaningful improvement in this project came from reading recorded
   reasoning: it caught a hallucinating agent, then caught my own mislabeled
   benchmark. History isn't a log. It's how the system gets better.
3. **Route by risk, not by habit.** qwen3.7-max where judgment matters,
   qwen3.7-plus with thinking disabled for triage and narration. Most payouts
   never touch the big model, and accuracy didn't suffer.

Everything above is replayable — the repo ships the actual event logs and a
**Replay Time Machine** UI that steps through any payout's real chain, disputed
negotiations included. Nothing in the demo is staged; the moment you mock up a
transcript, you've become the thing you're pitching against.

**Code:** https://github.com/Laolex/clearcrew (MIT)

*Built solo, July 2026, on qwen3.7-max and qwen3.7-plus via Qwen Cloud Model
Studio, deployed on Alibaba Cloud Function Compute.*
