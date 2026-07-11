# ClearCrew — Demo Video Storyboard

**Duration:** ~3.5 minutes
**Format:** 1080p screen recording with voiceover
**Target:** Devpost judges · Qwen Cloud Agent Society track

---

## Scene 1: The Problem (0:00–0:20)

| Visual | Audio |
|---|---|
| Black screen. Text fades in: *"When AI decides who gets paid…"* | "You're a payout ops team at a company moving money across borders." |
| Text changes: *"…can you trust the reason?"* | "We ran a single agent on the same batch ten times. It overdrew the treasury ten times out of ten. Once, by more than the entire balance." |
| Split screen: green checkmark fades → red X | "And when the agent is wrong, there's no why to retrieve, no trail to fix." |
| Fade to black. Logo: **ClearCrew** | "There's no way to point at a specific agent and say — fix that." |

---

## Scene 2: The Thesis (0:20–0:40)

| Visual | Audio |
|---|---|
| Architecture diagram appears (animated). 5 agent boxes animate in sequence. | "ClearCrew replaces the opaque single agent with a society of five specialists." |
| Intake box glows → Compliance → Treasury | "Intake triages. Compliance holds veto power—but must cite a rule. Treasury sequences funding under a reserve-floor waterfall." |
| Resolution box appears in a branch path | "When Compliance vetoes and Treasury disagrees, Resolution mediates—recorded." |
| Auditor box pulses | "Auditor explains every decision in plain English, after the fact." |
| All agents fade to reveal event log box at bottom: hash chain animates | "Every decision is an event in a hash-chained log. State is a fold over events. Any outcome can be replayed." |

---

## Scene 3: The Repair Ladder (0:40–1:20)

| Visual | Audio |
|---|---|
| Rapid screen recording: `python -m clearcrew.bench` | "The first run? Society lost. 58% to monolith's 83%. Compliance was vetoing on vibes." |
| Terminal output shows the miss table | "Fix: one written policy, vetoes must cite a rule, reject-by-default. Society 100% at n=12." |
| Second run: society drops one payout | "Then at n=36, the society drops one payout. Wrongly." |
| Replay UI opens, clicks on payout `5affb229`. Steps through events with arrow key | "And here's where the event log earns its keep. The chain is 5 events, all recorded." |
| Treasury event highlighted: shows hallucinated P2 violation | "Treasury hallucinated a policy rule that wasn't its job and overrode a correct compliance clearance." |
| Auditor event highlighted: reads "incorrect determination" | "The system caught its own agent. Unprompted, in plain English, in the same run." |
| Fade to: code diff — Treasury prompt changed | "Fix: one contract change. 'You decide funding and ONLY funding.' Error class gone." |
| Fade to: Treasury event shows "Reject." with action "pay_now" | "Later the trail caught Treasury's own reason contradicting its action. Machine-checkable." |
| Code diff: reconciliation guard added | "Fix: code flags, agents rule. Every treasury decision checked against deterministic arithmetic." |
| Benchmark table overlays: **Society 100.0% ± 0.0% — Monolith 87.5% ± 5.4%**, ten runs | "Ten runs of the final architecture. Society: a hundred percent, every time. Monolith: eighty-seven and a half, and one run that collapsed to seventy-two." |

---

## Scene 4: Accuracy Is the Wrong Unit (1:20–1:50)

The most important scene in the video. Do not rush it.

| Visual | Audio |
|---|---|
| Benchmark table still up. Highlight the monolith's **best** run: 91.7% | "Here's the trap. This is the single agent's best run. Ninety-two percent." |
| Cut to the treasury column for that same run: **−$9,460** | "It also ended nine thousand dollars in the hole — worse than four of its *lower*-scoring runs. Accuracy went up. The outcome got worse." |
| Ops page. The **eval bar** fills the frame. Press *fold the batch*; the bar drains toward the red floor line and holds at $15,540 | "So we stopped counting percentages and started folding the money. This is the treasury, falling as each recorded decision lands. The society stops here. Floor held." |
| Switch to run `20260702-204555`. Fold again — the bar drains straight *through* the floor and turns red: **−$14,460** | "This is one of our own early runs. Watch it go through the floor. We publish it. It's in the repo." |
| Zoom the gold note under the bar: *"treasury judged each payout alone in this run — it never recorded a running total"* | "And the record tells you exactly why: Treasury judged each payout on its own, and never wrote down a running total. Twenty-four times it said 'sufficient balance' — and every single time, about that one payout, it was right." |
| Text card: **the reserve floor is the one rule you cannot check one payout at a time** | "No single payout breaches the floor. The twenty-fourth one does." |

---

## Scene 5: Agents Propose. Policy Promotes. (1:50–2:20)

| Visual | Audio |
|---|---|
| Architecture diagram, the **Policy Gate** box lights up between the society and settlement | "So we fixed it structurally. Agents no longer decide. They propose." |
| Payout detail: three rows in sequence — *Society proposed: approve* → *Policy gate: REFUSED — P1* → *Decision: REJECTED* | "Every proposal passes through a deterministic gate. This one wanted to approve a sanctioned corridor. Policy refused it — and the refusal is on the record, in the agent's own words." |
| Ops list: the payout carries **both** a gold `blocked P1` chip and a red `miss` chip | "Note it's flagged twice. The treasury was protected, *and* an agent got it wrong. Two different facts. Both belong on the record." |
| Text card: **the gate is veto-only — it can refuse an approval, never create one** | "The gate can only ever refuse. If it could approve, it would be deciding — and the agents would be decorative." |
| Terminal: `pytest -k reserve_floor` passes | "So the reserve floor stops being a score and becomes an invariant. Here's the test: a society that proposes to approve *everything*. The floor still holds." |

---

## Scene 6: Real Settlement (2:20–2:45)

| Visual | Audio |
|---|---|
| Terminal: `python -m clearcrew.settle_demo` running | "But ClearCrew doesn't stop at decisions. Every approved verdict moves real money." |
| Terminal shows events streaming: `settlement.requested`, `settlement.confirmed` | "Run `settle_demo` and the society deliberates live—then Verasettle executes each approval as real USDC on Base Sepolia." |
| Terminal shows `payout.settled` with tx hash | "The settlement writes back into the same hash chain as the reasoning that caused it." |
| Base Sepolia explorer page opens for one tx | "You can verify these transfers on any public RPC. Don't trust me—ask the chain." |
| Fade to: replay UI showing the settled run, 41 events chain-verified | "The archived run: 41 events, chain verified. A sanctioned-corridor payout vetoed, two P2 violations rejected, three clean payouts on-chain." |
| Base Sepolia tx table shows 3 rows with links | "6/6 against ground truth. Real tx hashes, real money, real audit trail." |

---

## Scene 7: Replay Time Machine, and the Anchor (2:45–3:15)

| Visual | Audio |
|---|---|
| Browser opens `clearcrew.verasettle.com` | "And all of this is live at clearcrew.verasettle.com, deployed on Alibaba Cloud Function Compute." |
| Click on a run, click on a payout, step through events with keyboard | "The Replay Time Machine steps through any payout's real event chain. Arrow keys to navigate." |
| Click the counterfactual slider, drag reserve floor to $40k | "Want to know what would happen under different rules? Counterfactual replay: fold the recorded batch through hypothetical parameters—deterministic, no model re-runs." |
| UI shows 3 payouts flip to rejected | "Three $9,800 payouts flip. The rules changed, the history didn't." |
| Open a `chain.anchored` event; show `provider: freetsa.org`, a real `tsa_time`, and the token | "One more thing about that chain. A hash chain is written by the same process that writes the log — so anyone who could rewrite the file could rewrite the hashes too. So we don't only trust ourselves." |
| Terminal: `openssl ts -verify -in token.tsr -digest <head_hash>` → **Verification: OK** | "An independent timestamping authority signs our head hash with its own key. To rewrite this history you'd have to forge their signature. And you don't have to take our word for the check — that's openssl, not our code." |
| Open the MCP server terminal | "And the same read paths are exposed as an MCP server—so any agent framework can interrogate the audit trail as tools." |

---

## Scene 8: Judge Mode — The Live Run (3:15–3:35)

| Visual | Audio |
|---|---|
| Replay UI, click the ⚡ Live Run button | "There's one more thing. The live demo has a judge mode." |
| Enter access code | "Enter the access code from the submission notes, and it spawns a genuinely live 6-payout run." |
| UI shows events streaming in: intake → compliance → treasury → resolution → settlement | "Real Qwen calls, recorded disputes, real testnet settlement—streaming into your browser as the agents deliberate." |
| The run finishes, UI loads it for replay | "When it's done, your run loads for replay, hash-chained like every other. Nothing pre-recorded." |
| Fade to: split screen — society on left, monolith on right | "Nothing staged. If we mocked a transcript, we'd be the thing we're pitching against." |

---

## Scene 9: Close (3:35–3:50)

| Visual | Audio |
|---|---|
| Screen fades to black. Text appears: *"clearcrew.verasettle.com"* | "The single agent overdrew the treasury in ten runs out of ten, and could not tell you why. ClearCrew doesn't — and now, it can't." |
| Subtitle: *"MIT · Hash-chain verified · Testnet settled"* | "Hash-verified, privately auditable, and built so you can verify every claim yourself—with no API key, no trust, just a clone and `pytest`." |
| Stack logos: Qwen Cloud · Alibaba Cloud · Verasettle · Base Sepolia | "Built on Qwen Cloud for the Global AI Hackathon Series." |
| QR code to repo | "Full code at the link on screen. MIT. Step through a settlement yourself." |
| Fade to black | (silence) |

---

## Production Notes

- **Screen recordings** of the replay UI should use keyboard-driven navigation (arrows) where possible
- **Scene 4 is the video.** The repair ladder (scene 3) sets it up, but "its best run lost the most money" is the line judges will remember. Let the eval bar drain in real time — do not speed it up.
- **Never claim the gate fires often.** In all ten benchmark runs it blocked nothing, because the agents proposed correctly. Show the *adversarial test* instead (scene 5) and say so plainly. An invariant that never has to trigger is the point, not a weakness — but pretending it fires would be exactly the dishonesty this project exists to kill.
- **No mock data**: every screen showing events should be a real recorded run
- **Animate the architecture diagram** on screen with a stack: agents row → event log → settlement rail → replay UI
- **Macros**: `CMD+K` in replay UI opens counterfactual. `ESC` closes all modals
