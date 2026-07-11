# Benchmark Methodology

The claim under test: **is a society of specialist agents measurably safer than
one monolithic agent on the same task** — not "feels safer", measurably, with
the same policy, same models, same batch.

This page exists so the number can be attacked. Everything needed to reproduce
or falsify it is below, including the parts that don't flatter us.

## The setup

| | |
|---|---|
| **Task** | classify a batch of payout requests: approve or reject each, applying an org policy |
| **Batch** | `n=36` synthetic payouts, seeded (`data.make_batch`) — 6 corridors (one sanctioned), amounts $120–$15,000, recipient ages 2/30/400 days, some with missing memos |
| **Ground truth** | the **executable policy itself** (`policy.evaluate`) — see below |
| **Society** | 5 specialist Qwen agents + deterministic orchestrator (`agents.py`, `orchestrator.py`) |
| **Monolith** | one agent, one prompt, whole batch (`baseline.py`) |
| **Models** | identical for both: `qwen3.7-max` (strong), `qwen3.7-plus` (fast) |
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
architecture ten times and reports the spread.

## Accuracy is the wrong unit

Before the numbers, the finding that changed how we report them.

A payout system's job is not to be right on average. It is to not lose the
money. Those come apart, and this benchmark shows exactly where:

- The monolith's **best** accuracy run (92%) left the treasury at **−$9,460** —
  *worse* than four of its 89% runs. The metric went up while the outcome got
  worse, because **which** payouts you get wrong matters more than how many.
- Its worst run scored 72%, which reads like a passing grade, and ended the
  treasury at **−$113,660** — more than the entire opening balance.

So we report the closing treasury balance alongside the percentage. Percent
hides an insolvency; dollars do not.

## Results — ten runs of the current architecture

`scripts/bench_repeat.sh 10` — same batch, same policy, same models, ten times.
Every run is archived, including any we lose.

### Accuracy

| | mean | sd | min | max |
|---|---|---|---|---|
| **society** (proposals) | **100.0%** | 0.0% | 100.0% | 100.0% |
| **monolith** | 87.5% | 5.4% | **72.2%** | 91.7% |

The society wins **10/10**. Its spread is zero: the agents proposed the correct
verdict for all 36 payouts, ten times running. The monolith sits around 89% and
occasionally falls apart.

### Treasury outcome — the number that matters

Start $100,000. Reserve floor $10,000.

| | society | monolith |
|---|---|---|
| closing balance | **+$15,540**, every run | **negative, every run** |
| worst run | +$15,540 | **−$113,660** |
| reserve floor breached | **0 / 10** | **10 / 10** |

The single agent **overdraws the treasury in every run it has ever been given.**
Not occasionally — ten out of ten. Eight times it lands at −$4,460, once at
−$9,460, and once at −$113,660, which is more than the entire opening balance.

Note the run that scored its *best* accuracy (91.7%) closed at **−$9,460** —
worse than four of its 88.9% runs. The metric improved while the outcome got
worse, because **which** payouts you get wrong matters more than how many. That
is the whole argument for reporting dollars.

The society breached the floor zero times. After the policy gate it *cannot*:
no approval that P1/P2/P3 forbids can be recorded, whatever an agent proposes.

### The gate did not fire once in these ten runs — and that is not a problem

`blocked_by_policy` is **0** across all ten. The society proposed correctly every
time, so the gate had nothing to refuse. A fair reader will ask what it is for.

Three answers, all checkable:

1. **It is an invariant, not a feature that needs to trigger.** A seatbelt that
   never deploys is not a useless seatbelt. `test_reserve_floor_is_an_invariant_not_a_grade`
   builds the adversarial case — a society that proposes to approve *everything* —
   and the floor still holds; 6 of 12 approvals are refused.
2. **The failure it prevents is real and archived.** Two pre-gate runs
   (`20260702-204555`, `20260702-205623`) recorded approvals that overdrew the
   treasury, one by $24,460. We publish them. They are not expressible now.
3. **The monolith commits exactly this failure in all 10 runs.** The gate is the
   difference between a system that can overdraw and one that cannot.

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
| wall-clock (mean of 10) | 350 s | 141 s | **2.5× slower** |
| tokens | 84,676 | 13,403 | **6.3× more** |

**A caveat we owe you on the token row.** Token accounting was broken from
commit `3cb7e76` until `c1c4e14`: when the benchmark moved each system into its
own subprocess, `llm.usage_totals` stayed in the parent, so the counter read
zero and the token columns were deleted rather than plumbed across the boundary.
Every token figure quoted in between came from a run predating that change. The
counter is fixed, and the figures above are from the one run of these ten that
was recorded after the fix. They land at the same 6.3× as the old measurement,
which is corroboration rather than proof. Wall-clock is a mean over all ten.

Six times the tokens is a bad trade *if accuracy is all you're buying*. It isn't.
The extra tokens purchase the **record** — attributable reasoning, a recorded
veto, a ruling, a replayable chain — and, with the gate, an invariant: the
monolith overdrew the treasury in 10 of 10 runs and the society structurally
cannot. On a payout desk that is the entire product. On a task where nobody will
ever ask "why did this happen?" and nothing is at stake if it goes wrong, the
monolith is the correct choice and we would say so.

## Known limits of this benchmark

- **Synthetic batch.** Seeded generator, not production payout traffic. It
  exercises the policy's rule surface, not the messiness of real data.
- **Small n, and n=1 at the final config.** 36 payouts, and the current
  architecture has one recorded n=36 run. Enough to show a consistent gap across
  four governance versions; not enough for a confidence interval anyone should
  bet on.
- **Policy adherence, not judgment.** Ground truth is the mechanical policy.
  A payout that's *technically* approvable and *obviously* fraudulent scores as
  "approve" — the benchmark would not catch that, and neither system is being
  credited for it.
- **Same models both sides** is a strength for fairness and a limit for
  generality: this is evidence about *architecture*, not about Qwen.
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
