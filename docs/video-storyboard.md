# ClearCrew — Demo Video (Pitch Cut)

**Duration:** ~3 minutes
**Format:** 1080p screen recording with voiceover
**Target:** Devpost judges · Qwen Cloud Agent Society track

---

## The pitch in one line

> **A single AI agent overdrew the treasury in ten runs out of ten — and its
> best-scoring run lost the most money. ClearCrew makes that impossible, and
> lets you check.**

## Structure — this is an argument, not a tour

Six beats. Each one earns the next. Nothing is shown because it exists; every
screen is evidence for the sentence being spoken over it.

| beat | claim | evidence on screen |
|---|---|---|
| 1 | AI moving money is a trust problem, not an accuracy problem | the −$113,660 run |
| 2 | **The metric everyone reports is the wrong one** ← *the turn* | best accuracy run, worst money |
| 3 | Because one rule can't be judged one payout at a time | the eval bar draining |
| 4 | So we made breaking it structurally impossible | the policy gate refusing |
| 5 | And you never have to take our word for it | openssl verifying the anchor |
| 6 | Real verdicts, real money, one verifiable history | the Basescan tx |

**Do not open with the architecture.** Nobody buys an architecture. Open with
the money.

---

## Beat 1: The stakes (0:00–0:30)

| Visual | Audio |
|---|---|
| Black. Text: *"We gave one AI agent a batch of payouts. Ten times."* | "If you let an AI agent move money, the question isn't whether it's smart. It's whether you can prove what it did." |
| Text: *"It overdrew the treasury 10 times out of 10."* | "We ran a single agent — a good one — on the same batch of payouts, ten times. It overdrew the treasury every single time." |
| Number slams on: **−$113,660** | "Its worst run ended a hundred and thirteen thousand dollars in the hole. More than the entire opening balance." |
| Text: *"And it couldn't tell us why."* | "And it couldn't tell us why. No trail. No reasoning. No agent to fix." |
| Logo: **ClearCrew** | "ClearCrew." |

*No product, no architecture, no agents yet. Just the problem, in dollars.*

---

## Beat 2: The turn — you're measuring the wrong thing (0:30–1:00)

**The most important 30 seconds in the video. If only one beat lands, this one.**

| Visual | Audio |
|---|---|
| Benchmark table, ten runs: society **100.0% ± 0.0%**, monolith **87.5% ± 5.4%** | "Here's the benchmark. Five specialist Qwen agents against one big one. Same batch, same policy, same models. Ten runs." |
| Cursor hovers the monolith's **best** row: **91.7%** | "Now — this is the single agent's *best* run. Ninety-two percent. You'd ship that." |
| Cut to the treasury column for that same run: **−$9,460** | "It also lost more money than four of its *lower*-scoring runs." |
| Hold on it. Text card: **accuracy went up. the outcome got worse.** | "The metric went up. The outcome got worse. Because *which* payouts you get wrong matters more than *how many*." |
| Text card: **so we stopped counting percentages and started folding the money** | "Accuracy was hiding an insolvency. So we stopped reporting it." |

*Let the −$9,460 sit in silence for a full beat before the next line.*

---

## Beat 3: Why it fails — and why it isn't a prompting problem (1:00–1:35)

| Visual | Audio |
|---|---|
| Live site → Operations → the **eval bar**. Click *fold the batch*. The bar drains and holds above the red floor line at **$15,540** | "This is the treasury, falling as each recorded decision lands. The society stops here. Floor held." |
| Switch to run `20260702-204555` — **one of ours** — and fold again. The bar drains straight *through* the floor and turns red: **−$14,460** | "Now one of our *own* early runs. Watch it go through the floor. We publish this. It's in the repo." |
| Zoom the gold note under the bar: *"treasury judged each payout alone — it never recorded a running total"* | "And the record says exactly why. Our Treasury agent judged each payout on its own. Twenty-four times it said 'sufficient balance' — and every single time, about that one payout, it was right." |
| Text card: **no single payout breaches the floor. the twenty-fourth one does.** | "The reserve floor is the one rule you cannot check one payout at a time. A local reasoner is blind to it — and you cannot prompt your way out of a context problem." |

*Show our own failure before our fix. Publishing the broken run is the
credibility that makes beat 4 land.*

---

## Beat 4: The fix — agents propose, policy promotes (1:35–2:10)

| Visual | Audio |
|---|---|
| Payout detail, three rows in sequence: *Society proposed: approve* → *Policy gate: **REFUSED — P1*** → *Decision: REJECTED* | "So agents don't decide anymore. They propose. A deterministic gate promotes the proposal — or refuses it, and the refusal goes on the record in the agent's own words." |
| Ops list: the payout carries **both** a gold `blocked P1` chip **and** a red `miss` chip | "Flagged twice, deliberately. The treasury was protected — *and* an agent got it wrong. Two different facts. Both belong on the record." |
| Text card: **veto-only — it can refuse an approval, never create one** | "The gate can only ever refuse. If it could approve, it would be doing the deciding — and the five agents would be decorative." |
| Terminal: `pytest -k reserve_floor` → **passed** | "Here's a society that proposes to approve *everything*. The floor holds anyway." |
| Text card: **the reserve floor is now an invariant, not a score** | "It stopped being something we measure, and became something the system cannot do. That run that overdrew by twenty-four thousand? It is no longer expressible." |

**Say this out loud — do not skip it:** *"In all ten benchmark runs, the gate
blocked nothing. The agents proposed correctly every time."* A seatbelt that
never deploys is still doing its job — and claiming otherwise would be exactly
the dishonesty this project exists to kill.

---

## Beat 5: Don't trust us — check (2:10–2:40)

| Visual | Audio |
|---|---|
| A `chain.anchored` event: `provider: freetsa.org`, a real `tsa_time`, the token | "Every decision is hash-chained. But *we* write that chain — so we could rewrite it. A hash chain on its own only stops someone who can't edit the file." |
| Terminal: `openssl ts -verify -in token.tsr -digest <head_hash>` → **Verification: OK** | "So we don't only trust ourselves. An independent timestamping authority signs our head hash with its own key. To rewrite this history, you'd have to forge *theirs*." |
| Point at the terminal | "And that's openssl checking it. Not our code. You never have to trust us for the part that matters." |

---

## Beat 6: Real money, live (2:40–3:00)

| Visual | Audio |
|---|---|
| Deep link `#events-20260703-165045-settled-n6.jsonl/1818e811`. Step to the teal **VERASETTLE** event, click the tx hash, let Basescan load | "And verdicts move real money. This nine-thousand-eight-hundred-dollar approval executed as testnet USDC on Base Sepolia — and the receipt lives in the *same* tamper-evident chain as the reasoning that caused it." |
| Live site, ⚡ **Live Run** button | "The demo has a judge mode: a genuinely live run — real Qwen calls, real recorded disputes, real settlement — streaming as the agents deliberate. Nothing pre-recorded." |
| Black. Text: **clearcrew.verasettle.com** | "The single agent overdrew the treasury in ten runs out of ten, and couldn't tell you why." |
| Text: *"Decisions over money — replayable by construction."* | "ClearCrew doesn't. And now — it can't." |

---

## Production notes

- **Beat 2 is the video.** If it doesn't land, nothing after it matters.
- **Let the eval bar drain in real time.** Do not speed it up. Four seconds of
  the bar falling toward the red line is the most persuasive footage available.
- **Show our failure before our fix.** Beat 3 before beat 4, always.
- **Never imply the gate fires often.** It blocked nothing in all ten runs. Show
  the adversarial test instead and say so on camera. A judge who runs the
  benchmark will find `blocked_by_policy: 0` in every result file — and if the
  video implied otherwise, every other claim we made becomes suspect.
- **Every number on screen must be reproducible** from `scripts/bench_stats.py`
  or a `runs/*.jsonl` file. If it isn't, cut it.
- **No architecture diagram before beat 4**, if at all. The diagram explains
  *how*; the money explains *why anyone should care*. Lead with why.
- Screen recordings: keyboard-driven where possible, cursor slow and deliberate,
  1920×1080, bookmarks bar hidden. Record the live deploy — judges recognize the
  URL.

## If you have to cut to 2 minutes

Keep beats **1, 2, 3, 6**. Drop beat 5 (the anchor) and compress beat 4 to the
single *proposed → REFUSED → rejected* screenshot. The argument survives intact:
here's what it costs, here's why, here's it not happening, here's real money.

## What the old cut got wrong (kept as a note to self)

The previous storyboard was a feature tour: seven scenes, each demoing a thing
the repo contains — replay, counterfactual, MCP, settlement. It opened with the
architecture. It was accurate and it was boring, because it asked the judge to
assemble the argument themselves. The repair-ladder narrative (the self-caught
hallucination, the "…Reject." / `pay_now` contradiction) is still the best
*writing* in this project — it lives in [demo-notes.md](demo-notes.md) and the
[blog post](blog-post.md), where a reader has time for it. A three-minute video
does not. Pick one argument, prove it, stop.
