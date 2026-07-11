---
title: "The night my AI agent caught another AI agent lying"
description: "My best-scoring AI agent lost the most money. Building an agent society for payout operations on Qwen Cloud — and what the event log taught me that no eval score could."
published: false
tags: [ai, agent, qwen, provenance, hackathon]
cover_image: https://clearcrew.verasettle.com/img/devto-cover.png
series: Agent Society Deep-Dive
---

# The night my AI agent caught another AI agent lying — building ClearCrew on Qwen Cloud

*Building an agent society for payout operations for the Qwen Cloud Global AI Hackathon — and what the event log taught me that no eval score could.*

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

![The recorded chain of payout 5affb229 — Compliance clears it correctly, Treasury hallucinates a P2 violation on a $5,000 payout, and the Auditor flags the incorrect determination unprompted](https://clearcrew.verasettle.com/img/devto-caught-lie.png)

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

Fixed the labels to model the full policy. Score at that point:

| batch | society | monolith |
|---|---|---|
| n=12 | 100% | 100% |
| n=36 | **100%** | **89%** |

At real batch sizes the single agent fails in both directions: it overdraws the
treasury *and* strands clean payouts, with no recoverable explanation for
either. The society gets all 36 — including the two rejections that require
doing waterfall arithmetic across the entire batch.

(Hold onto that 89%. It turns out to be a much worse number than it looks, and
I didn't find out until I stopped trusting it.)

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

## Round five: history became executable

Once the log was trustworthy, two things fell out almost for free.

First, **policy became data**. The written policy the agents are prompted with
is now rendered from a versioned `PolicyVersion` object, every run opens with a
`policy.enacted` event recording the parameters in force, and the same
`evaluate()` function that labels the benchmark's ground truth can re-fold any
recorded batch under *hypothetical* parameters. Ask the replay UI "what would
this exact batch have done under a $40,000 reserve floor?" and it answers
deterministically: three specific $9,800 payouts flip to rejected, rule P3,
recorded outcomes untouched. No model re-runs, no simulated realities —
arithmetic over history.

Second, and this is the part I didn't expect to pull off inside a hackathon:
**the verdicts started moving real money.** I wired the orchestrator to a
settlement rail — [Verasettle](https://verasettle.com), a non-custodial USDC
payout orchestrator I also build, called strictly through its public API, no
shared code — and ran a fresh six-payout batch end to end. The society vetoed
a sanctioned-corridor payout, rejected two policy violations, and the three
clean approvals executed as **real testnet USDC transfers on Base Sepolia**.
Each settlement wrote back into the *same hash chain* as the reasoning that
caused it: `settlement.requested` → `settlement.confirmed` (carrying the
on-chain tx hash and the rail's receipt) → `payout.settled`. You can verify
the transfers on any public Base Sepolia RPC without trusting me at all.

Judgment, verdict, and money movement — one tamper-evident history. That
sentence is the whole project.

And because "trust me, it works" is exactly the thing this project exists to
kill, the deployed demo has a **judge mode**: an access-coded button that
spawns a genuinely live run — real Qwen calls, real recorded disputes, real
settlement — and streams the events into your browser as the agents
deliberate, then hands you the finished run to replay, hash-chained like
every other. Nothing pre-recorded about it.

## Round six: the number I'd been reporting was the wrong one

One run is an anecdote, so I ran the final architecture ten times.

| | mean | sd | min | max |
|---|---|---|---|---|
| society | **100.0%** | 0.0% | 100.0% | 100.0% |
| monolith | 87.5% | 5.4% | **72.2%** | 91.7% |

Good. Ship it. Except — I'd built an eval bar for the UI by then (a
chess-engine-style vertical bar showing the treasury balance falling as each
recorded decision folds in), and to build it I had to fold the *monolith's*
decisions into a treasury balance too.

Here is what fell out:

| | society | monolith |
|---|---|---|
| closing balance | **+$15,540**, every run | **negative, every run** |
| worst run | +$15,540 | **−$113,660** |
| reserve floor breached | **0 / 10** | **10 / 10** |

The single agent overdraws the treasury in **every run it has ever been given**.
Ten out of ten. Once by more than the entire opening balance.

And then the detail that actually changed how I think about evals. The
monolith's **best** accuracy run — 91.7%, its high-water mark — closed the
treasury at **−$9,460**. That's *worse* than four of its 88.9% runs.

**The metric went up while the outcome got worse.** Because which payouts you
get wrong matters more than how many.

I had been reporting accuracy for weeks. Accuracy was hiding an insolvency.

The failure isn't even noisy — it's structural. The monolith misses the same
four payouts every stable run: it approves *both* $15,000 P3 payouts, and
rejects two clean $5,000 payouts by over-applying P2. Look at which rule it
can't see: **P3, the reserve floor — the only rule in the policy that cannot be
evaluated one payout at a time.** No single payout breaches the floor. The
twenty-fourth one does.

A single agent reasoning locally is blind to the one globally-scoped rule. That
is not a prompting problem. You cannot prompt your way out of a context problem.

## Round seven: grading is not governing

Here's the thing that embarrasses me most in hindsight. My policy engine was a
**grader**. It ran *after* the agents, told me whether they'd been right, and
scored them. That's how two of my own archived runs recorded approvals that
overdrew the treasury — nothing was stopping them. I was writing a very
sophisticated post-mortem.

So agents stopped deciding. Now they **propose**:

```
treasury.decided          →  the agent's judgment
payout.proposed  approve  →  what the society WANTS to do
policy.blocked   P3       →  the reserve floor refuses it — recorded, not hidden
payout.rejected           →  the terminal decision
```

Only the deterministic policy layer can promote a proposal into a recorded
decision. **The reserve floor stopped being a score and became an invariant.**
The run that overdrew by $24,460 is no longer *expressible*.

Two design constraints kept this honest, and I'd get both wrong if I did it
again without thinking:

**The gate is veto-only.** It can refuse an approval; it can never manufacture
one. The policy layer models arithmetic — not judgment, not disputes, not the
soft flags the agents exist to weigh. A gate that could *approve* would be
deciding rather than constraining, and the five agents would be decorative.

**The benchmark had to move upstream.** This one nearly got me. If the gate
refuses every approval the policy forbids, then terminal decisions agree with
policy *by construction* — so if I kept scoring terminal decisions, the society
would report **100% forever**, and I'd be measuring my own gate while calling it
the agents. The number would be unfalsifiable, which for a benchmark is the same
as worthless. So the benchmark now scores the **proposal**: what the agents
actually judged, before governance had its say. An agent can still be wrong, and
the record still says so — a blocked payout carries *both* a "blocked" flag and
a "miss" flag, because the treasury was protected **and** an agent got it wrong.
Those are two different facts and both belong on the record.

Full disclosure, because it cuts against me: in all ten benchmark runs, the gate
blocked **nothing**. The agents proposed correctly every time. A seatbelt that
never deploys is still doing its job — and the adversarial test (a society that
proposes to approve *everything*; the floor holds anyway) is in the repo — but I
am not going to pretend it fires when it doesn't.

## Round eight: my tamper-evident log wasn't

I'd been saying "tamper-evident hash chain" for weeks. Then I read my own
threat model with fresh eyes and realised it was overselling a sha256 loop.

The chain is computed by the **same process that writes the log**. So anyone who
can write that file can edit event 12, recompute every hash after it, and
produce a chain that verifies perfectly clean. It stops accidents. It stops a
naive edit. It does not stop an adversary with write access — which is precisely
the adversary an auditor cares about.

The honest version of my pitch was: *"you don't have to believe the agents, you
can replay them — as long as you trust whoever holds the file."* Smaller claim.
Still a good one. But not the one I was making.

Closing it needs exactly one thing: a copy of the head hash held somewhere I
can't reach. **No blockchain required** — [RFC-3161](https://www.rfc-editor.org/rfc/rfc3161)
has done this since 2001. An independent Time Stamping Authority signs
`(my head hash, its clock)` with *its* key:

```json
{"type": "chain.anchored", "actor": "anchor", "payload": {
  "provider": "https://freetsa.org/tsr",
  "head_hash": "7317a904276619230a99331b755d612d0351d7f79706cc1ac6fe7681046ae2c0",
  "tsa_time":  "20260711172852Z",
  "token":     "3082121e30030201..."}}
```

To rewrite an anchored run you'd now have to forge freetsa.org's signature. And
you don't have to trust my verification code either — the token is standard:

```bash
openssl ts -verify -in token.tsr -digest <head_hash> -CAfile tsa-ca.pem
```

Two footnotes I owe you. The RFC-3161 client I'd stubbed out weeks earlier was
**broken** — it POSTed a urlencoded form where the spec wants DER-encoded ASN.1,
and 404'd on contact. It had never once run. And when I wrote a real one, I
cross-checked my response parser against `openssl ts -reply` — which caught a bug
in *my* code: I was reading `TSTInfo`'s first INTEGER as the serial number, but
that field is the version, so every token would have reported serial `1`. Both
of those are arguments for the same thing: **check your proofs against something
that isn't yours.**

## What I actually learned

1. **Agent societies don't win by default.** Ungoverned, mine lost badly. The
   wins came from the boring institutional stuff: written policy, cited rules,
   separation of duties, rejected-by-default.
2. **The audit trail is not a compliance checkbox — it's the debugging tool.**
   Every meaningful improvement in this project came from reading recorded
   reasoning: it caught a hallucinating agent, then caught my own mislabeled
   benchmark, then caught the fact that I was reporting the wrong metric
   entirely. History isn't a log. It's how the system gets better.
5. **Pick the unit your user actually loses.** I reported accuracy for weeks
   because accuracy is what benchmarks report. The monolith's best-scoring run
   lost the most money. If your system can fail expensively, measure the
   expense — not the percentage.
6. **Grading is not governing.** A policy engine that runs *after* the agents
   tells you that you lost the money. One that runs *between* the agents and the
   money means you can't. Invariants beat benchmark percentages, and it's a
   twenty-line change.
7. **Check your proofs against something that isn't yours.** My hash chain
   couldn't survive an attacker with write access, and my timestamp client had
   never successfully run. Both were found by reaching for an outside tool —
   an independent authority, and `openssl`.
3. **Route by risk, not by habit.** qwen3.7-max where judgment matters,
   qwen3.7-plus with thinking disabled for triage and narration. Most payouts
   never touch the big model, and accuracy didn't suffer.
4. **Decision and execution belong in separate accountable layers.** ClearCrew
   never holds funds and Verasettle never judges; the API boundary between
   them is the same separation-of-duties idea that fixed Treasury, applied one
   level up. The event log is what binds the layers together.

Everything above is replayable — the repo ships the actual event logs and a
**Replay Time Machine** UI that steps through any payout's real chain, disputed
negotiations and on-chain settlements included. Nothing in the demo is staged;
the moment you mock up a transcript, you've become the thing you're pitching
against.

**Live demo:** https://clearcrew.verasettle.com
**Code:** https://github.com/Laolex/clearcrew (MIT)

*Built solo, July 2026, on qwen3.7-max and qwen3.7-plus via Qwen Cloud Model
Studio, deployed on Alibaba Cloud Function Compute, settling through
Verasettle on Base Sepolia.*
