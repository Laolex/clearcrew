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

**The honest limitation:** the current architecture (run 4) has exactly **one**
recorded n=36 run. One run at 100% is a promising result, not an established
one. We have not repeated it enough times to put an error bar on it, and we
would not defend "100%" as the society's true accuracy — only as what it scored,
on this batch, with the chain verified.

## The cost, stated plainly

The society is not free. On the headline run:

| | society | monolith | ratio |
|---|---|---|---|
| accuracy (n=36) | 100% | 89% | **+11 pts** |
| tokens | 76,113 | 12,068 | **6.3× more** |
| wall-clock | 323 s | 150 s | **2.2× slower** |

Six times the tokens for eleven points of accuracy is a bad trade *if accuracy is
all you're buying*. It isn't. What the extra tokens purchase is the **record**:
attributable reasoning, a recorded veto, a ruling, and a replayable chain — the
difference between an error you can locate and an error you can't. On a payout
desk that difference is the entire product. On a task where nobody will ever be
asked "why did this happen?", the monolith is the correct choice and we'd say so.

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
