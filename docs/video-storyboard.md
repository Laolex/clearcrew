# ClearCrew — Demo Video (Pitch Cut)

**Duration:** ~3 minutes
**Format:** 1080p screen recording with voiceover
**Target:** Devpost judges · Qwen Cloud Agent Society track

Every visual in this script has been checked against the live site and the
archived runs. If a beat is not here, it is not recordable — see
[What this cut deliberately does not claim](#what-this-cut-deliberately-does-not-claim).

---

## The pitch in one line

> **A single AI agent overdrew the treasury in ten runs out of ten and left no
> role-attributed trail. Five agents caught each other — on a record you can replay.**

## Structure — this is an argument, not a tour

Five beats. Each one earns the next. Nothing is shown because it exists; every
screen is evidence for the sentence being spoken over it.

| beat | claim | evidence on screen | time |
|---|---|---|---|
| 1 | AI moving money is a trust problem, not an accuracy problem | the −$113,660 run | 0:25 |
| 2 | **The metric everyone reports is the wrong one** ← *the turn* | best-accuracy run, worse money | 0:40 |
| 3 | **A society catches what one agent structurally cannot** ← *the proof* | `62c33a4f` — one agent overruling another | 0:50 |
| 4 | And we made the loss unexpressible, not just unlikely | the policy gate + the passing test | 0:35 |
| 5 | Real verdicts, real money, one verifiable history | the tamper demo + the Basescan tx | 0:30 |

**Do not open with the architecture.** Nobody buys an architecture. Open with
the money. **Beat 3 is where the track's brief gets answered** — it is the only
beat where the *society* is the point, and it is the one to protect if you run
long.

**The terminal is the hero of beats 2 and 4.** `scripts/bench_stats.py` prints
the entire benchmark argument — accuracy, the treasury table, the gate's honesty
note — from the archived runs, live, in one command. A judge can run it
themselves. That is worth more than any animation we could build.

---

## Before you record — the one-time setup

Beats 2 and 4 are terminal shots. Stage them so nothing is typed twice on camera:

```bash
cd /opt/qwen-agent-society

# beat 2 — the whole benchmark argument, printed from runs/ on disk
python3 scripts/bench_stats.py

# beat 4 — the invariant, proved by test
cd src && API_KEY="" ../.venv/bin/python -m pytest -k reserve_floor -q   # → 3 passed
```

Both are verified working as of this cut. Font size up, prompt short, `clear`
between beats.

**There are no deep links.** The app holds view/run/subject in React state — there
is no hash routing, so a URL fragment will not open a payout. Navigate by
clicking, and rehearse the path so it's smooth on camera:

| beat | click path |
|---|---|
| 3 | **Qwen society** → *Open the recorded reconciliation dispute `62c33a4f`* |
| 4 | **Benchmark** → *Open the gated-monolith record `62c33a4f`* |
| 5 | **Run trail** → run `20260703-165045-settled-n6` → payout **`1818e811`** → the teal **VERASETTLE** event |

If you want the raw record on screen instead of the UI, the API is one GET and
returns the whole chain — it makes a good B-roll cutaway:

```
curl -s clearcrew.verasettle.com/api/runs/events-20260711-173828-n36.jsonl/explain/62c33a4f
```

---

## Beat 1: The stakes (0:00–0:25)

| Visual | Audio |
|---|---|
| Black. Text: *"We gave one AI agent a batch of payouts. Ten times."* | "If you let an AI agent move money, the question isn't whether it's smart. It's whether you can prove what it did." |
| Text: *"It overdrew the treasury 10 times out of 10."* | "We ran a single agent — a good one — on the same batch, ten times. It overdrew the treasury every single time." |
| Number slams on: **−$113,660** | "Its worst run ended a hundred and thirteen thousand dollars in the hole. More than the entire opening balance. And it left no replayable record of who made the mistake or how to fix it." |
| Logo: **ClearCrew** | "ClearCrew." |

*No product, no architecture, no agents yet. Just the problem, in dollars.*

---

## Beat 2: The turn — you're measuring the wrong thing (0:25–1:05)

Run `python3 scripts/bench_stats.py`. Everything below is on that one screen —
let it print, then walk the cursor down it.

| Visual | Audio |
|---|---|
| Top table: society **100.0% ± 0.0%**, monolith **87.5% ± 5.4%**, over **10 runs** | "Here's the benchmark. Five specialist Qwen agents against one Qwen agent. Same batch, same written policy, same Qwen model family — printing live from the archived logs, not from a slide." |
| Per-run table, land on `20260711-182815` — the monolith's **best** run: **91.7%** | "This is the single agent's *best* run. Ninety-two percent. You'd ship that." |
| Treasury table, same run id: **−$9,460** | "It also lost more money than *eight* of its worse-scoring runs. They each landed at minus four thousand. This one — the good one — lost nine." |
| Hold. Text card: **accuracy went up. the outcome got worse.** | "The metric went up. The outcome got worse. Because *which* payouts you get wrong matters more than *how many*." |
| Cursor down the **monolith floor** column — `BREACHED` ten times | "Ten runs, ten breaches. Not variance. Not a bad prompt." |
| Text card: **no single payout breaches the floor. the twenty-fourth one does.** | "The reserve floor is the one rule you cannot check one payout at a time. Each payout looks affordable alone — it's the running total that kills you. A reasoner reading one payout at a time is blind to it, and you cannot prompt your way out of a context problem." |

*Let the −$9,460 sit in silence for a full beat before the next line.*

> **Accuracy check for the voiceover.** Eight runs scored 88.9% and landed at
> −$4,460. One scored 91.7% (best) and landed at −$9,460. One scored 72.2%
> (worst) and landed at −$113,660. So: the best-accuracy run lost more than
> eight worse-scoring runs — but it did **not** lose the most. Say "more than
> eight of its worse-scoring runs," never "lost the most money."

---

## Beat 3: The society — one agent catches another (1:05–1:55)

**This is the beat the track is scoring, and the only one where the society is
the point. If you run long, cut from beat 4, not here.**

**Qwen society** → *Open the recorded reconciliation dispute `62c33a4f`*. Walk down the
recorded chain: a **$15,000 aid disbursement, Germany → Kenya, on a 400-day-old
account**. Every line below is verbatim from the log.

| Visual | Audio |
|---|---|
| **Qwen society** — configured runtime and the five role boundaries | "ClearCrew runs five specialist Qwen roles. Intake classifies, Compliance can veto, Treasury funds, Resolution rules, and Auditor explains. No role can quietly do another role's job." |
| `[intake]` — *"Destination country KE is not sanctioned (P1). Recipient account age (400 days) exceeds the 7-day threshold, so P2 does not apply."* → **fast-tracked** | "Watch a real payout move through the society. Intake checks it: not sanctioned, account's over a year old. Clean. The system fast-tracks it to Treasury; no deep compliance review is needed." |
| `[treasury]` — **action: `pay_now`** · reason: *"Cumulative total 99460.0 > headroom 90000.0"* | "Then Treasury. And read this carefully, because it's the whole project in two lines. Its *reason* says the cumulative total is over the headroom — which is the exact condition that requires a rejection. And its *action* says: pay now." |
| Hold on the contradiction. Text card: **it said "reject." it did "approve."** | "It got the reasoning right and the answer wrong. It contradicted itself, in writing." |
| `[orchestrator]` — **`reconciliation.flagged`** | "Nobody prompted it to notice. The orchestrator reconciles what agents *say* against what they *do* — and these didn't match." |
| `[resolution]` — **`enforce_ledger`** — *"Treasury's action of 'pay_now' contradicts its own stated reason… The ledger check is correct; treasury's action is wrong."* | "So it goes to an independent agent. Resolution rules against Treasury — by name, citing the rule, on the record." |
| `[orchestrator]` — **`payout.rejected`** · `[auditor]` — *"…a dispute resolution process corrected this error by enforcing the ledger's rejection rule."* | "Rejected. And the Auditor writes down what happened in plain English, so a human doesn't have to read any of this." |
| Text card: **a monolith has no second reader** | "This is what the society adds here: a second reader, a deterministic check, and a recorded appeal. The single agent made this class of mistake alone; ClearCrew gives the error somewhere to go." |

> **Say the honest version — do not skip it:** across every archived run,
> Resolution ruled **149 times to uphold a compliance veto** and **twice to
> overrule an agent**. It is not a debating society; it mostly agrees. On
> camera: *"in the recorded runs, Resolution upheld nearly every veto it saw —
> this is one of two cases where it ruled against one of our own agents, and
> both are in the repo."* Rare and recorded beats frequent and asserted.

---

## Beat 4: The fix — agents propose, policy promotes (1:55–2:30)

| Visual | Audio |
|---|---|
| **Benchmark** → *Inspect the guardrail* → note that society needed **0** policy blocks in ten runs | "Catching a mistake after the fact still isn't good enough. And we don't credit the society for safety the gate provides: in these ten society runs, the agents proposed correctly, so the gate did not have to intervene." |
| **Benchmark** → *Open the gated-monolith record `62c33a4f`* → *proposed* → *policy gate* → *rejected* | "To test the guardrail fairly, we gave the single agent the same gate. Its invalid approval is recorded, blocked under P3, and cannot execute." |
| Text card: **veto-only — it can refuse an approval, never create one** | "The gate can only ever refuse. If it could approve, it would be doing the deciding — and the five agents would be decorative." |
| Terminal: `pytest -k reserve_floor` → **3 passed** | "Here's a society that proposes to approve *everything*. The floor holds anyway. The reserve floor stopped being something we measure and became something the system cannot do." |

**Say this out loud — do not skip it:** *"In all ten society benchmark runs,
the gate blocked nothing: the agents proposed correctly every time. This separate
gated-monolith run proves the guardrail itself."* The benchmark output says
*policy gate refused an approval in 0 runs*. A judge who runs it will find
`blocked_by_policy: 0` in every society result file; do not imply the gate
rescued a society benchmark run.

---

## Beat 5: Don't trust us — check (2:30–3:00)

| Visual | Audio |
|---|---|
| **Evidence** tab → click **tamper** → verification fails from that event onward | "Every decision is hash-chained, and every hash is recomputed in *your* browser, not on our server. Rewrite one reason and the chain breaks exactly there. You don't have to trust us for the part that matters." |
| **Run trail** → `20260703-165045-settled-n6` → payout `1818e811` → the teal **VERASETTLE** event → click the tx hash → Basescan | "And verdicts move real money. This nine-thousand-eight-hundred-dollar approval executed as testnet USDC on Base Sepolia — at a recorded ten-thousand-to-one scale, which is in the event too. The receipt lives in the *same* tamper-evident chain as the reasoning that caused it." |
| **Overview**: *22 runs · 629 payouts · 100% hash-verified · 100% replayable* | "Twenty-two recorded runs. Six hundred and twenty-nine payouts. Every one replayable, every hash verified — counted off the logs on disk." |
| Black. Text: **clearcrew.verasettle.com** | "One agent overdrew the treasury ten times out of ten and left no role-attributed trail." |
| Text: *"Decisions over money — replayable by construction."* | "Five agents caught each other. And wrote it down." |

---

## What this cut deliberately does not claim

Read this before you improvise on camera. Each line is something an earlier
storyboard claimed that the shipped product does not do:

- **There is no live-run / judge mode.** No "⚡ Live Run" button exists. The
  public site is replay plus a sandboxed client-side simulation. Never say
  "nothing pre-recorded" — everything on screen *is* recorded, and that is the
  point, not a weakness.
- **"Try it" is sandboxed and says so.** It labels itself *No funds move* and
  *Settled · simulated*. If you demo it, use its own words.
- **The Benchmark tab shows accuracy, tokens, and seconds — not money.** The
  treasury numbers live in `bench_stats.py` and `docs/BENCHMARK.md`. Show them
  there. Do not imply the UI has a money column.
- **Resolution rarely overturns.** 149 upholds, 2 overrules, 0 compliance-veto
  reversals. Beat 3 shows one of the two. Say that it's rare.
- **The society is not cheaper and not faster.** 2.5× wall-clock, 6.3× tokens.
  Say it before a judge finds it. What it buys is a record you can replay.
- **Tokens were captured for only 1 of 10 runs** (accounting was broken across
  the subprocess boundary until `c1c4e14`). If the 6.3× appears on screen, that
  caveat is printed directly beneath it — don't crop it out.
- **There are no shareable deep links.** View, run, and subject live in React
  state; nothing is in the URL. Don't put a fragment URL on screen or in the
  Devpost writeup expecting it to open a payout — it won't. Navigate by clicking,
  or show the `/api/runs/{run}/explain/{payout}` GET, which does work.

## Production notes

- **Beat 3 is the differentiator; beat 2 is the hook.** Beat 2 earns attention,
  beat 3 earns the score. Protect both.
- **Show our failure before our fix.** The self-contradiction (beat 3) and the
  benchmark misses (beat 4) both come before the gate. Publishing the broken run
  is the credibility that makes the fix land.
- **Every number on screen must be reproducible** from `scripts/bench_stats.py`
  or a `runs/*.jsonl` file. If it isn't, cut it.
- **No architecture diagram.** The diagram explains *how*; the money explains
  *why anyone should care*, and beat 3 explains *why a society*. Lead with why.
- Screen recordings: keyboard-driven where possible, cursor slow and deliberate,
  1920×1080, bookmarks bar hidden. Record the live deploy — judges recognize the
  URL.

## If you have to cut to 2 minutes

Keep beats **1, 2, 3**, and the last two rows of **5**. Drop beat 4 entirely.
The argument survives: here's what it costs, here's why the metric lied, here's
five agents catching what one cannot, here's real money and a chain you can
break yourself.

## What got cut from this cut, and why

**The RFC-3161 anchor beat** (openssl verifying a freetsa.org token against our
head hash → `Verification: OK`) is real, it works, and it is the strongest
trust claim in the project — a hash chain we write only stops someone who can't
edit the file; an independent authority's signature stops someone who can. It
lost its slot to beat 3 because the track scores *agent society* at 60%
(technical depth + innovation) and the anchor argues provenance, not society.
It still lives in `README.md`, `docs/TRUST_MODEL.md`, and the Devpost writeup.
If you ever cut a 4-minute version, it goes back in between beats 4 and 5.

## Notes to self

The pre-Jul-16 cut was written against a UI that no longer exists: it opened a
beat on an "Operations" tab and an animated eval bar draining through the floor,
and closed on a live-run button. None of those shipped. It also claimed the
monolith's best-scoring run "lost the most money" — the data says otherwise (the
*worst*-scoring run did), the kind of error any judge running `bench_stats.py`
would have caught. And it spent three minutes proving the *money* argument while
naming the five agents exactly once, in passing — a society video in which the
society never appears.

The repair-ladder narrative (the self-caught Treasury hallucination) is still
the best *writing* in this project — it lives in [demo-notes.md](demo-notes.md)
and the [blog post](blog-post.md), where a reader has time for it. Beat 3 is its
30-second cut: same lesson, one payout, no exposition.
