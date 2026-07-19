# Benchmark Methodology

The claim under test *used* to be: **is a society of specialist agents measurably
safer than one monolithic agent?** Running the ablation killed that question. A
single agent with the same policy gate is exactly as safe — the gate does that
work, and any architecture can have one.

So here is the claim as the evidence actually supports it:

> **Governance makes a system safe. Judgment makes it correct. They are different
> problems, and only one of them is solved by adding agents.**

Measured, on the same batch, same policy, same models:

- **The gate** takes a single agent from breaching the reserve floor **11/11 runs
  to 0/11**. Safety is architecture-independent.
- **The society** proposes correctly **100.0%** of the time against the
  monolith's **87.6%** — worth **$8,636 per run** in legitimate payouts that a
  gated monolith strands and no gate can rescue.

This page exists so both numbers can be attacked. Everything needed to reproduce
or falsify them is below, including the parts that don't flatter us — and the
ablation is one of those parts.

## The setup

| | |
|---|---|
| **Task** | classify a batch of payout requests: approve or reject each, applying an org policy |
| **Batch** | `n=36` synthetic payouts, seeded (`data.make_batch`) — 6 corridors (one sanctioned), amounts $120–$15,000, recipient ages 2/30/400 days, some with missing memos |
| **Ground truth** | the **executable policy itself** (`policy.evaluate`) — see below |
| **Society** | 5 specialist Qwen agents + deterministic orchestrator (`agents.py`, `orchestrator.py`) |
| **Monolith** | one agent, one prompt, whole batch (`baseline.py`) |
| **Models** | identical for both: `qwen3.7-max` (strong), `qwen3.7-plus` (fast). Run 11 (`20260719-192857`) used `qwen-plus` as the fast model — DashScope's free tier for `qwen3.7-plus` was exhausted; the strong model, which does all monolith and all heavy society reasoning, was unchanged |
| **Policy** | identical for both — the *same rendered text* is injected into both prompts |
| **Isolation** | each system runs in its own subprocess with its own event log, so token counters, timing, and memory never cross-contaminate (`bench.py`) |
| **Reproduce** | `DASHSCOPE_API_KEY=… python -m clearcrew.bench` |

## Ground truth: the label and the counterfactual share one implementation

The benchmark's labels are not hand-written. `policy.evaluate()` — the same
function the counterfactual replay engine calls — assigns each payout its
expected verdict:

```python
verdicts = policy.evaluate(batch)          # P1 sanctions, P2 threshold, P3 waterfall
for p in batch:
    p["_expected"] = verdicts[p["id"]]["verdict"]
```

This matters: **labels and the replay engine cannot drift apart**, because
they are the same code path. It also means the benchmark measures *policy
adherence*, not "was the decision wise" — that's the honest scope of the claim.

## What is scored: the proposal, not the outcome

This changed when the policy gate landed, and the reason is worth stating
plainly because it is a trap we nearly walked into.

The gate refuses to record an approval the policy forbids. So **terminal
outcomes now agree with policy by construction** — if we kept scoring them, the
society would report 100% forever, and we would be measuring the gate while
calling it the agents. The number would be unfalsifiable, which for a benchmark
is the same as worthless.

So the benchmark scores `payout.proposed` — what the society actually judged,
before governance had its say:

```python
society_decisions = society_result["proposals"]     # what the agents wanted
```

An agent can still propose something wrong, and the record still says so. The
gate stops the money; it does not launder the mistake. In the console a blocked
payout carries **both** a `blocked P1` chip and a `miss` chip, because two
different things are true: the treasury was protected, *and* an agent was wrong.

The monolith has no gate and no proposals, so it is scored exactly as before —
on the decisions it actually produced. Both systems are therefore graded on
their own judgment, which is the only comparison that means anything.

## Results — read these as a ladder, not as trials

The four recorded n=36 runs are **not four samples of one system**. Each is a
different governance version, and each fix was diagnosed from the previous run's
recorded trail. Averaging them would blend v1 with v4 and mean nothing.

| run | governance in place | society | monolith |
|---|---|---|---|
| `20260702-152154` | written policy · cited vetoes · separation of duties | 100.0% | 88.9% |
| `20260702-204555` | same, fresh run (first hash-chained) | 94.4% | 91.7% |
| `20260702-205623` | + agents judge, ledgers add (deterministic cumulative ledger) | 97.2% | 88.9% |
| `20260702-210640` | + code flags, agents rule (treasury reconciled against ledger) | **100.0%** | 88.9% |

The last row is the current architecture, and it is the headline. See the repair
ladder in the [README](../README.md) for what each run's trail caught.

Two things worth reading off this table honestly:

- **The society's dip in run 2 is the interesting result, not an embarrassment.**
  It regressed because Treasury was judging payouts one at a time and breaching
  the reserve floor — and we know that *because the trail said so*, in Treasury's
  own recorded words ("sufficient balance", ×24). The fix was governance, not a
  prompt tweak.
- **The monolith wobbles between 88.9% and 91.7% and never explains itself.**
  Its variance is the same size as some of our fixes, and there is nothing to
  read and nobody to fix.

**That limitation is now closed.** The section below repeats the *current*
architecture eleven times and reports the spread.

## Accuracy is the wrong unit

Before the numbers, the finding that changed how we report them.

A payout system's job is not to be right on average. It is to not lose the
money. Those come apart, and this benchmark shows exactly where:

- The monolith's **best** accuracy run (92%) left the treasury at **−$9,460** —
  *worse* than nine of its 89% runs. The metric went up while the outcome got
  worse, because **which** payouts you get wrong matters more than how many.
- Its worst run scored 72%, which reads like a passing grade, and ended the
  treasury at **−$113,660** — more than the entire opening balance.

So we report the closing treasury balance alongside the percentage. Percent
hides an insolvency; dollars do not.

## Results — eleven runs of the current architecture

`scripts/bench_repeat.sh` — same batch, same policy, same models, eleven times.
Every run is archived, including any we lose.

### Accuracy

| | mean | sd | min | max |
|---|---|---|---|---|
| **society** (proposals) | **100.0%** | 0.0% | 100.0% | 100.0% |
| **monolith** | 87.6% | 5.2% | **72.2%** | 91.7% |

The society wins **11/11**. Its spread is zero: the agents proposed the correct
verdict for all 36 payouts, eleven times running. The monolith sits around 89% and
occasionally falls apart.

### Treasury outcome — the number that matters

Start $100,000. Reserve floor $10,000.

| | society | monolith |
|---|---|---|
| closing balance | **+$15,540**, every run | **negative, every run** |
| worst run | +$15,540 | **−$113,660** |
| reserve floor breached | **0 / 11** | **11 / 11** |

The single agent **overdraws the treasury in every run it has ever been given.**
Not occasionally — eleven out of eleven. Nine times it lands at −$4,460, once at
−$9,460, and once at −$113,660, which is more than the entire opening balance.

Note the run that scored its *best* accuracy (91.7%) closed at **−$9,460** —
worse than nine of its 88.9% runs. The metric improved while the outcome got
worse, because **which** payouts you get wrong matters more than how many. That
is the whole argument for reporting dollars.

The society breached the floor zero times. After the policy gate it *cannot*:
no approval that P1/P2/P3 forbids can be recorded, whatever an agent proposes.

### The ablation: how much of that is the society, and how much is the gate?

The table above is **not a fair fight**, and it took a reviewer to make us say so.
Only one of those systems has a policy gate. The gate is
**architecture-independent** — `_promote()` refuses a forbidden approval no matter
who proposed it — so putting "society 0/10" next to "monolith 10/10" silently
credits the society with the gate's work.

So we settled it with an experiment instead of a disclaimer. `baseline_gated.py`
is the monolith with the same gate bolted on. `scripts/ablation.py` folds each of
the ten **recorded** monolith decision sets through it — the gate is
deterministic, so nothing is re-run and nothing is simulated. (One live
end-to-end gated run is archived too:
`events-20260711-195934-gated-mono-n36.jsonl`. It agrees exactly.)

| | monolith | monolith **+ gate** | society |
|---|---|---|---|
| reserve floor breached | **10 / 10** | **0 / 10** | **0 / 10** |
| legitimate payouts **stranded** (mean of 10) | — | **$8,500** | **$0** |
| judgment (proposal accuracy, mean of 10 × 36 payouts) | 87.5% | 87.5% | **100.0%** |
| closing balance (typical run) | −$4,460 | +$25,540 | +$15,540 |

**Read the two dollar figures carefully — they are from different columns.**
$25,540 is one typical run; $8,500 is the mean of ten. They are not meant to
match, and per-run they reconcile as an exact identity:

> **gated balance = society balance + stranded.** Every row. No exceptions.

That is not a coincidence — it is the veto-only property restated as arithmetic.
The society pays everything it owes, so its closing balance *is* the correct one.
Every dollar the gated monolith holds above it is a dollar it owed someone and
refused. Here is the full ablation, so the identity can be checked row by row:

| run | monolith | monolith **+ gate** | society | blocked | **stranded** |
|---|---|---|---|---|---|
| `20260711-173828` | −$4,460 | $25,540 | $15,540 | 2 | $10,000 |
| `20260711-174646` | −$4,460 | $25,540 | $15,540 | 2 | $10,000 |
| `20260711-175456` | −$4,460 | $25,540 | $15,540 | 2 | $10,000 |
| `20260711-180309` | −$4,460 | $25,540 | $15,540 | 2 | $10,000 |
| `20260711-181100` | −$113,660 | **$15,540** | $15,540 | **10** | **$0** |
| `20260711-181947` | −$4,460 | $25,540 | $15,540 | 2 | $10,000 |
| `20260711-182815` | −$9,460 | $20,540 | $15,540 | 2 | $5,000 |
| `20260711-183603` | −$4,460 | $25,540 | $15,540 | 2 | $10,000 |
| `20260711-184356` | −$4,460 | $25,540 | $15,540 | 2 | $10,000 |
| `20260711-185226` | −$4,460 | $25,540 | $15,540 | 2 | $10,000 |

Mean stranded: **$8,500** = (8 × $10,000 + $5,000 + $0) / 10.

**1. The treasury protection is the gate's.** It takes the single agent from
10/10 breaches to 0/10, refusing an average of 2.8 of its approvals per run. A
gated monolith is *safe*. Any architecture can have this, and a committee of
agents is not what keeps money in the vault.

**2. But the gated monolith closes *richer* — and that is bad, not good.**
$25,540 against the society's $15,540. A higher balance means money that should
have gone out didn't. The gate is **veto-only** by design: it can refuse a payout
that breaks the rules; it can never *rescue* one that was wrongly refused. The
gated monolith holds the floor **by not paying people it owes** — $8,500 of
legitimate payouts stranded, every run. The society strands $0.

**3. So the claims separate cleanly, and both survive:**

| | what it buys | who can have it |
|---|---|---|
| **the gate** | you cannot pay the wrong people | any architecture |
| **the society** | you *do* pay the right people, and can prove why | judgment — no gate substitutes for it |

The society's honest claim is therefore about **judgment, not safety**: 100.0% vs
87.5% on proposals, worth $8,500 a run in payouts that would otherwise be
stranded, plus an attributable record for every call. That is a smaller claim than
the raw treasury table implies, and it is the one the evidence actually supports.

### The strongest attack on this thesis is in our own data: run `20260711-181100`

Find it in the table above. It is the monolith's **worst** judgment run — 72.2%
accuracy, −$113,660 unaided, the catastrophe. Under the gate it closes at
**$15,540 with $0 stranded**: level with the society, on every metric we report.

The mechanism is not luck, and it is worth being blunt about. That run approved
almost *everything*. So it never wrongly **rejected** anything — nothing to
strand — and its 10 bad approvals were all mechanically forbidden, so the gate
caught all 10. **Its recklessness is precisely what made the gate look perfect.**

Which means: on this benchmark, **"rubber-stamp every payout and let the gate
sort it out" is an optimal strategy.** It ties the society. We are not going to
bury that, so here is why it does not rescue the monolith — and where it *does*
bite us:

1. **It is an artifact of the ground truth, not a real strategy.** Our labels
   *are* the executable policy (`policy.evaluate`), and the gate enforces that
   same function. So a rubber stamp plus a *complete* gate is optimal **by
   construction** — we have defined the test such that the gate can catch
   everything. That is a limitation of the benchmark, not a virtue of the
   rubber stamp.
2. **Real gates are never complete.** A gate encodes the subset of policy that
   is expressible as code. Judgment is required exactly where the rules are
   *not* mechanizable — the payout that is technically approvable and obviously
   fraudulent (already listed under Known limits). A rubber stamp scores 100%
   here and is worthless there, and **this benchmark cannot see the difference.**
3. **It is not free even here.** A system that approves everything produces a
   record in which every `payout.proposed` is identical and no reasoning is
   attributable. You cannot ask it why. The 10 other runs show the monolith's
   *actual* behaviour, which strands $9,500 on average — the rubber stamp is a
   strategy it fell into once, catastrophically, not one it reliably executes.

The honest reading: **our benchmark rewards a degenerate strategy, and we can see
it doing so.** Closing that hole means ground truth that is *not* identical to
the gate — a policy with a judgment-shaped hole in it that no code can check.
That is the next experiment, and it is not done. Until it is, the judgment claim
rests on the ten runs where the monolith behaved like a monolith rather than a
coin flip.

### The tier ablation: drop the model, keep the architecture

A fair reviewer asked the inverse question: the gate ablation shows the *gate*
is separable — is the *model*? If the judgment layer is really load-bearing,
weakening it should show up in the numbers.

So we ran the same benchmark with **both systems on `qwen-turbo`** — the cheap
tier — three times (`CLEARCREW_MODEL_STRONG=qwen-turbo CLEARCREW_MODEL_FAST=qwen-turbo`,
archived in `runs-ablation/`, deliberately kept out of `runs/` so the headline
distribution stays single-config):

| proposal accuracy | on `qwen3.7-max` | on `qwen-turbo` (3 runs) |
|---|---|---|
| **monolith** | 87.6% ± 5.2% | **64.8% ± 1.6%** |
| **society** | **100.0% ± 0.0%** | **100.0% ± 0.0%** |

Two findings, and they point in the same direction:

1. **Judgment is model-bound.** Drop the tier and the single agent loses
   **23 points** — the same batch it scored 87.6% on collapses to 64.8%. Whatever
   the monolith's competence is, it lives in the model, and there is no
   architecture underneath to catch it falling.
2. **The society's structure recovers the cheap model.** Decomposition into
   narrow specialist calls, the deterministic cumulative ledger, reconciliation,
   and adjudicated disputes turn the *same* qwen-turbo into a system that
   proposed all 36 verdicts correctly, three runs out of three — at ~73k tokens
   and **49 seconds** a run, seven times faster than the strong-tier society.

The honest boundary: this is one seeded batch and the ground truth is the
mechanizable policy (see Known limits) — "turbo society scores 100%" is bounded
by the same limit as every other accuracy claim here. What the ablation does
establish is the causal direction: **the model tier moves the monolith by 23
points and the society by zero.** The society is what makes model judgment
survivable; the model is what makes the monolith's number.

### The gate did not fire once in the society's eleven runs — and that is not a problem

`blocked_by_policy` is **0** across all eleven. The society proposed correctly every
time, so the gate had nothing to refuse. A fair reader will ask what it is for.

Four answers, all checkable:

1. **It is an invariant, not a feature that needs to trigger.** A seatbelt that
   never deploys is not a useless seatbelt. `test_reserve_floor_is_an_invariant_not_a_grade`
   builds the adversarial case — a society that proposes to approve *everything* —
   and the floor still holds; 6 of 12 approvals are refused.
2. **The failure it prevents is real and archived.** Two pre-gate runs
   (`20260702-204555`, `20260702-205623`) recorded approvals that overdrew the
   treasury, one by $24,460. We publish them. They are not expressible now.
3. **The monolith commits exactly this failure in all 11 runs.** The gate is the
   difference between a system that can overdraw and one that cannot.
4. **You can watch it fire on a real recorded run.** In the gated-monolith
   ablation (`events-20260711-195934-gated-mono-n36.jsonl`) the gate refuses two
   $15,000 reserve-floor approvals — real events, `policy.blocked`, rule P3,
   attributed to the monolith. Open it in the console and step through it.

### What the monolith actually does

Its failure is **structural, not noisy**. In its stable runs it misses the
same four payouts every single time:

| payout | amount | policy | monolith | the error |
|---|---|---|---|---|
| `62c33a4f` | $15,000 | reject — **P3** | approved | reserve floor |
| `dbf4a8b2` | $15,000 | reject — **P3** | approved | reserve floor |
| `6bf46c69` | $5,000 | approve | rejected | over-applied P2 |
| `5affb229` | $5,000 | approve | rejected | over-applied P2 |

The two it wrongly *approves* are **both** of the P3 payouts — the one rule in
the policy that cannot be evaluated one payout at a time. The two it wrongly
*rejects* are clean $5,000 payouts to 2-day-old recipients: it sees "new
recipient" and rejects, though P2 only bites at ≥ $9,000.

That is the whole thesis in one table. A single agent reasoning locally is blind
to the only globally-scoped rule, and no amount of prompt tuning fixes a context
problem. The society's deterministic ledger sees the batch; the policy gate then
makes the floor an invariant rather than a hope.

### The earlier repair ladder (pre-gate, kept for the record)

These four runs are **not** samples of one system — each is a different
governance version, diagnosed from the previous run's trail. Averaging them
would blend v1 with v4 and mean nothing. They are scored on terminal decisions
(there was no gate yet), so they are not comparable with the ten runs above.

| run | governance in place | society | monolith |
|---|---|---|---|
| `20260702-152154` | written policy · cited vetoes · separation of duties | 100.0% | 88.9% |
| `20260702-204555` | same, fresh run (first hash-chained) | 94.4% | 91.7% |
| `20260702-205623` | + agents judge, ledgers add (deterministic cumulative ledger) | 97.2% | 88.9% |
| `20260702-210640` | + code flags, agents rule (treasury reconciled against ledger) | 100.0% | 88.9% |

The society's dip in run 2 is the interesting row, not an embarrassment: it
regressed because Treasury judged payouts one at a time and breached the floor —
and we know that *because the trail said so*, in Treasury's own recorded words
("sufficient balance", ×24). The fix was governance, not a prompt tweak.

## The cost, stated plainly

The society is not free.

| | society | monolith | ratio |
|---|---|---|---|
| wall-clock (mean of 11) | 350 s | 143 s | **2.5× slower** |
| tokens (mean of the 2 measured runs) | 86,292 | 12,846 | **6.7× more** |

**A caveat we owe you on the token row.** Token accounting was broken from
commit `3cb7e76` until `c1c4e14`: when the benchmark moved each system into its
own subprocess, `llm.usage_totals` stayed in the parent, so the counter read
zero and the token columns were deleted rather than plumbed across the boundary.
Every token figure quoted in between came from a run predating that change. The
counter is fixed, and the figures above are the mean of the two runs of these
eleven recorded after the fix (they measure 6.3× and 7.2× individually). They
bracket the old measurement, which is corroboration rather than proof.
Wall-clock is a mean over all eleven.

Six times the tokens is a bad trade *if accuracy is all you're buying*. It isn't.
The extra tokens purchase the **record** — attributable reasoning, a recorded
veto, a ruling, a replayable chain — and, with the gate, an invariant: the
monolith overdrew the treasury in 11 of 11 runs and the society structurally
cannot. On a payout desk that is the entire product. On a task where nobody will
ever ask "why did this happen?" and nothing is at stake if it goes wrong, the
monolith is the correct choice and we would say so.

## Known limits of this benchmark

- **Synthetic batch.** Seeded generator, not production payout traffic. It
  exercises the policy's rule surface, not the messiness of real data.
- **Small batch, eleven runs.** Every accuracy figure here is the mean of **11
  runs × 36 payouts** (~400 decisions) at the current config — not a handful of
  calls. But it is still one seeded 36-payout batch: enough for the spread we
  report (society sd 0.0%, monolith sd 5.2%), not enough for a confidence
  interval anyone should bet real money on.
- **Policy adherence, not judgment — and this is the load-bearing limit.**
  Ground truth is the mechanical policy, and the gate enforces that same
  function. A payout that's *technically* approvable and *obviously* fraudulent
  scores as "approve", and neither system is credited for catching it. This is
  what lets a rubber stamp tie the society in run `20260711-181100` (see the
  ablation). **Any claim we make about "judgment" is bounded by the fact that our
  ground truth is mechanizable.** Fixing it requires a policy with a
  judgment-shaped hole no code can check. Not done.
- **Same models both sides** is a strength for fairness and a limit for
  generality: within one tier, this is evidence about *architecture*. The tier
  ablation above adds the model-axis evidence — drop the tier and the monolith
  moves 23 points while the society moves zero — but it is Qwen-tier-vs-Qwen-tier,
  not Qwen-vs-another-provider.
- **We report every run we have.** No run was discarded; the four above are
  all four `results-*.json` files in `runs/`.

## Why the failures are the interesting part

The society's misses are recorded, attributed, and explained — which is how we
found the real bug. In one run, Treasury rejected a clean $5,000 payout citing
"P2 violation: amount >= 9000 USD". Compliance had already cleared it,
correctly. The Auditor flagged the contradiction *unprompted*, in the same run:
"…an **incorrect determination** that the amount violated the P2 policy limit."

That trail didn't just explain the failure — it prescribed the fix (Treasury
was re-litigating another agent's domain; one contract change removed the whole
error class). The monolith made errors in the same runs, and they were silent.

That asymmetry — **accountable failure vs. silent failure** — is what the
accuracy column can't show you, and it's the actual claim.
