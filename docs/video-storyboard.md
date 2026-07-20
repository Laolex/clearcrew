# ClearCrew — Demo Video (Pitch Cut)

**Duration:** ~3 minutes
**Format:** 1080p screen recording with voiceover
**Target:** Devpost judges · Qwen Cloud Agent Society track

Every visual in this script has been checked against the live site and the
archived runs. If a beat is not here, it is not recordable — see
[What this cut deliberately does not claim](#what-this-cut-deliberately-does-not-claim).

---

## The pitch in one line

> **A single AI agent overdrew the treasury in eleven runs out of eleven and
> couldn't say why. Five agents caught each other — on a record you can replay.**

And the headline the whole cut builds to (say it verbatim in beat 4):

> **The policy gate makes payouts safe; Qwen judgment makes them correct.**
> Give the single agent the same gate and it strands **$8,636 of legitimate
> payouts per run**. The Qwen society strands **$0**.

## Structure — this is an argument, not a tour

Five beats. Each one earns the next. Nothing is shown because it exists; every
screen is evidence for the sentence being spoken over it.

| beat | claim | evidence on screen | time |
|---|---|---|---|
| 1 | AI moving money is a trust problem, not an accuracy problem | the −$113,660 run | 0:25 |
| 2 | **The metric everyone reports is the wrong one** ← *the turn* | best-accuracy run, worse money | 0:40 |
| 3 | **A society catches what one agent structurally cannot** ← *the proof* | `62c33a4f` — one agent overruling another | 0:50 |
| 4 | **The gate makes payouts safe; Qwen judgment makes them correct** ← *the headline* | `ablation.py`: $8,636 stranded vs $0 + the passing test + tier ablation | 0:45 |
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

# beat 4 — the headline, printed from the recorded monolith decisions
python3 scripts/ablation.py

# beat 4 — the invariant, proved by test
cd src && API_KEY="" ../.venv/bin/python -m pytest -k reserve_floor -q   # → 3 passed
```

Both are verified working as of this cut. Font size up, prompt short, `clear`
between beats.

**There are no deep links.** The app holds view/run/subject in React state — there
is no hash routing, so a URL fragment will not open a payout. Navigate by
clicking, and rehearse the path so it's smooth on camera:

| beat | click path (re-driven on the LIVE site Jul 20, headless) |
|---|---|
| 3 | **Exceptions** → *disputes resolved* → payout **`62c33a4f`** (run `20260711-173828`) |
| 5 tamper | landing page **Enter the console** → sidebar **Evidence** → red button **"rewrite the reason at index 41"** (there is no button labeled "tamper"; the run selector defaults to the newest run — fine). The break card + "restore the real log" render as audited. |
| 5 settlement | sidebar **Run trail** → run **`20260703-165045-settled-n6`** → scroll to the **SETTLEMENT** section → click timeline row **036 `settlement.confirmed`** (teal **VS Verasettle**, subject `1818e811`) to EXPAND it → RAIL / CHAIN `BASE-SEPOLIA` / `TX_HASH 0xee004e08…` / EXPLORER URL all on screen |

**Fixed on the live deploy Jul 20 (commit `f2f069f`, re-verified live headless):**
- The Basescan URL in the expanded `settlement.confirmed` row is now a **real
  clickable link** — "click the tx hash → Basescan" works as scripted. (Backup if
  the click misbehaves on camera: `https://sepolia.basescan.org/tx/0xee004e0813fd239840821471f5c70752bb963264df3cfea65dbeab37a7d96866`.)
  Clicking the payout id `1818e811` opens the decision drawer — good B-roll for
  the 8-event chain, but the tx lives in the timeline row, not the drawer.
- The Evidence page's noop anchor now reads neutral **"NO EXTERNAL ANCHOR — a
  placeholder anchor was recorded for this run"** instead of red ANCHOR INVALID.
  Safe to scroll the whole page on camera.
- The console **sidebar is now sticky** — it stays pinned while the main pane
  scrolls, so long Run-trail scrolls keep the nav in frame.

If you want the raw record on screen instead of the UI, the API is one GET and
returns the whole chain — it makes a good B-roll cutaway:

```
curl -s clearcrew.verasettle.com/api/runs/events-20260711-173828-n36.jsonl/explain/62c33a4f
```

---

## Beat 1: The stakes (0:00–0:25)

| Visual | Audio |
|---|---|
| Black. Text: *"We gave one AI agent a batch of payouts. Eleven times."* | "If you let an AI agent move money, the question isn't whether it's smart. It's whether you can prove what it did." |
| Text: *"It overdrew the treasury 11 times out of 11."* | "We ran a single agent — a good one — on the same batch, eleven times. It overdrew the treasury every single time." |
| Number slams on: **−$113,660** | "Its worst run ended a hundred and thirteen thousand dollars in the hole. More than the entire opening balance. And it couldn't tell us why — no trail, no reasoning, no agent to fix." |
| Logo: **ClearCrew** | "ClearCrew." |

*No product, no architecture, no agents yet. Just the problem, in dollars.*

---

## Beat 2: The turn — you're measuring the wrong thing (0:25–1:05)

Run `python3 scripts/bench_stats.py`. Everything below is on that one screen —
let it print, then walk the cursor down it.

| Visual | Audio |
|---|---|
| Top table: society **100.0% ± 0.0%**, monolith **87.6% ± 5.2%**, over **11 runs** | "Here's the benchmark. Five specialist Qwen agents against one big one. Same batch, same policy, same models — printing live from the archived logs, not from a slide." |
| Per-run table, land on `20260711-182815` — the monolith's **best** run: **91.7%** | "This is the single agent's *best* run. Ninety-two percent. You'd ship that." |
| Treasury table, same run id: **−$9,460** | "It also lost more money than *nine* of its worse-scoring runs. They each landed at minus four thousand. This one — the good one — lost nine." |
| Hold. Text card: **accuracy went up. the outcome got worse.** | "The metric went up. The outcome got worse. Because *which* payouts you get wrong matters more than *how many*." |
| Cursor down the **monolith floor** column — `BREACHED` eleven times | "Eleven runs, eleven breaches. Not variance. Not a bad prompt." |
| Text card: **no single payout breaches the floor. the twenty-fourth one does.** | "The reserve floor is the one rule you cannot check one payout at a time. Each payout looks affordable alone — it's the running total that kills you. A reasoner reading one payout at a time is blind to it, and you cannot prompt your way out of a context problem." |

*Let the −$9,460 sit in silence for a full beat before the next line.*

> **Accuracy check for the voiceover.** Nine runs scored 88.9% and landed at
> −$4,460. One scored 91.7% (best) and landed at −$9,460. One scored 72.2%
> (worst) and landed at −$113,660. So: the best-accuracy run lost more than
> nine worse-scoring runs — but it did **not** lose the most. Say "more than
> nine of its worse-scoring runs," never "lost the most money."

---

## Beat 3: The society — one agent catches another (1:05–1:55)

**This is the beat the track is scoring, and the only one where the society is
the point. If you run long, cut from beat 4, not here.**

**Exceptions** → *disputes resolved* → payout **`62c33a4f`**. Walk down the
recorded chain: a **$15,000 aid disbursement, Germany → Kenya, on a 400-day-old
account**. Every line below is verbatim from the log.

| Visual | Audio |
|---|---|
| `[intake]` — *"Destination country KE is not sanctioned (P1). Recipient account age (400 days) exceeds the 7-day threshold, so P2 does not apply."* → **fast-tracked** | "Watch a real payout move through the society. Intake checks it: not sanctioned, account's over a year old. Clean. Compliance agrees — fast-tracked. No veto. On any single-agent system, this payment is already out the door." |
| `[treasury]` — **action: `pay_now`** · reason: *"Cumulative total 99460.0 > headroom 90000.0"* | "Then Treasury. And read this carefully, because it's the whole project in two lines. Its *reason* says the cumulative total is over the headroom — which is the exact condition that requires a rejection. And its *action* says: pay now." |
| Hold on the contradiction. Text card: **it said "reject." it did "approve."** | "It got the reasoning right and the answer wrong. It contradicted itself, in writing." |
| `[orchestrator]` — **`reconciliation.flagged`** | "Nobody prompted it to notice. The orchestrator reconciles what agents *say* against what they *do* — and these didn't match." |
| `[resolution]` — **`enforce_ledger`** — *"Treasury's action of 'pay_now' contradicts its own stated reason… The ledger check is correct; treasury's action is wrong."* | "So it goes to an independent agent. Resolution rules against Treasury — by name, citing the rule, on the record." |
| `[orchestrator]` — **`payout.rejected`** · `[auditor]` — *"…a dispute resolution process corrected this error by enforcing the ledger's rejection rule."* | "Rejected. And the Auditor writes down what happened in plain English, so a human doesn't have to read any of this." |
| Text card: **a monolith has no second reader** | "This is what a society buys you that a bigger model cannot. The single agent made this same mistake — but it was the only one in the room. There was nobody to catch it, and nothing to read afterward." |

> **Say the honest version — do not skip it:** across every archived run,
> Resolution ruled **158 times to uphold a compliance veto** and **twice to
> overrule an agent**. It is not a debating society; it mostly agrees. On
> camera: *"in the recorded runs, Resolution upheld nearly every veto it saw —
> this is one of two cases where it ruled against one of our own agents, and
> both are in the repo."* Rare and recorded beats frequent and asserted.

---

## Beat 4: The headline — the gate makes payouts safe; Qwen judgment makes them correct (1:55–2:40)

| Visual | Audio |
|---|---|
| **Run trail** → a rejected payout: *proposed* → *policy gate* → *rejected* | "So agents don't decide anymore. They propose. A deterministic gate promotes the proposal — or refuses it, and the refusal goes on the record. Veto-only: it can refuse an approval, never create one." |
| Terminal: `pytest -k reserve_floor` → **3 passed** | "Here's a society that proposes to approve *everything*. The floor holds anyway. The overdraft stopped being something we measure and became something the system cannot do." |
| Terminal: `python3 scripts/ablation.py` — land on **stranded (mean): monolith+gate $8,636 · society $0** | "So is the society just the gate in a costume? We checked. Give the single agent the *same* gate, and it never breaches the floor either — but look how it does it. It closes *richer* than the society, and that's bad: it holds the floor by refusing to pay people it owed. Eight thousand six hundred dollars of legitimate payouts stranded, every run. The Qwen society strands zero — its gate never fired once in eleven runs." |
| Text card: **the gate makes payouts safe. Qwen judgment makes them correct.** | "The gate makes payouts safe. Qwen judgment makes them correct. You need both — and only one of them can be written as a rule." |
| Carousel panel 07 (or the `docs/BENCHMARK.md` tier table): **monolith 87.6 → 64.8 · society 100.0 → 100.0** | "And the judgment really is the model's. Drop both systems to qwen-turbo and the single agent falls twenty-three points. The society still proposes every verdict correctly — the structure makes the model's judgment survivable." |

**Say this out loud — do not skip it:** *"In all eleven benchmark runs, the
society's gate blocked nothing. The agents proposed correctly every time."* It's
printed right there in the `bench_stats.py` output — *policy gate refused an
approval in 0 runs*. A seatbelt that never deploys is still doing its job, and a
judge who runs the benchmark will find `blocked_by_policy: 0` in every result
file. If the video implied otherwise, every other claim we made becomes suspect.

*(Cut for time if needed: the "benchmark misses" Exceptions-tab row from the old
cut — the honesty point is now carried by the ablation itself. The tier-ablation
row is the last to add, first to drop; it survives in `docs/BENCHMARK.md` and
the Devpost writeup.)*

---

## Beat 5: Don't trust us — check (2:40–3:10)

| Visual | Audio |
|---|---|
| **Evidence** tab → click **tamper** → verification fails from that event onward | "Every decision is hash-chained, and every hash is recomputed in *your* browser, not on our server. Rewrite one reason and the chain breaks exactly there. You don't have to trust us for the part that matters." |
| **Run trail** → `20260703-165045-settled-n6` → payout `1818e811` → the teal **VERASETTLE** event → click the tx hash → Basescan | "And verdicts move real money. This nine-thousand-eight-hundred-dollar approval executed as testnet USDC on Base Sepolia — at a recorded ten-thousand-to-one scale, which is in the event too. The receipt lives in the *same* tamper-evident chain as the reasoning that caused it." |
| **Overview**: *23 runs · 666 payouts · 100% hash-verified · 100% replayable* | "Twenty-three recorded runs. Six hundred and sixty-six payouts. Every one replayable, every hash verified — counted off the logs on disk." |
| Black. Text: **clearcrew.verasettle.com** | "One agent overdrew the treasury eleven times out of eleven and couldn't tell you why." |
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
- **Resolution rarely overturns.** 158 upholds, 2 overrules, 0 compliance-veto
  reversals. Beat 3 shows one of the two. Say that it's rare.
- **The society is not cheaper and not faster.** 2.5× wall-clock, 6.7× tokens.
  Say it before a judge finds it. What it buys is a record you can replay.
- **Tokens were captured for only 2 of 11 runs** (accounting was broken across
  the subprocess boundary until `c1c4e14`). If the 6.7× appears on screen, that
  caveat is printed directly beneath it — don't crop it out.
- **The tier ablation is Qwen-tier vs Qwen-tier**, not Qwen vs another
  provider. Say "drop the tier" — never claim a cross-provider comparison.
- **No `override_with_conditions` exists in any recorded run.** The two
  overrules are both `enforce_ledger`. Don't imply negotiated middle-ground
  outcomes on camera.
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

## Timing note (Jul 20)

This cut now runs **~3:10**. If the form enforces a hard 3:00, drop beat 4's
tier-ablation row (−15s) first — it survives in `docs/BENCHMARK.md` and the
Devpost writeup. **Never drop the ablation/headline row**; it is the argument.

## If you have to cut to 2 minutes

Keep beats **1, 2, 3**, the **ablation + headline rows of 4**, and the last two
rows of **5**. Drop the rest of beat 4. The argument survives: here's what it
costs, here's why the metric lied, here's five agents catching what one cannot,
here's why the gate alone isn't the answer, here's real money and a chain you
can break yourself.

## What got cut from this cut, and why

**The RFC-3161 anchor beat** (openssl verifying a freetsa.org token against our
head hash → `Verification: OK`) is real, it works, and it is the strongest
trust claim in the project — a hash chain we write only stops someone who can't
edit the file; an independent authority's signature stops someone who can. It
lost its slot to beat 3 because the track scores *agent society* at 60%
(technical depth + innovation) and the anchor argues provenance, not society.
It still lives in `README.md`, `docs/TRUST_MODEL.md`, and the Devpost writeup.
If you ever cut a 4-minute version, it goes back in between beats 4 and 5.
