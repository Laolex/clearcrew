import { Link } from 'react-router-dom'

export function Landing() {
  const faqs = [
    ['What does ClearCrew record?', 'Every intake, compliance check, treasury decision, orchestration step, and settlement result is written as an append-only event.'],
    ['Can I verify a past payout?', 'Yes. The console replays recorded events into state and checks the hash chain, so a payout can be inspected without asking an agent to explain itself again.'],
    ['Does replay change the original run?', 'Never. Replays are read-only. Counterfactuals evaluate a different deterministic policy without modifying the recorded history.'],
    ['Where does Verasettle fit in?', 'ClearCrew produces the evidence trail and approval state; Verasettle executes only the settlement that the recorded process approved.'],
  ]

  return (
    <main className="landing">
      <div className="landing-atmosphere" aria-hidden="true"><i /><i /><i /></div>
      <header className="landing-topbar">
        <span className="landing-mark">ClearCrew <small>by Verasettle</small></span>
        <Link className="landing-nav-cta" to="/console">Enter the console →</Link>
      </header>

      <section className="landing-hero">
        <p className="eyebrow">Proof layer for autonomous payouts</p>
        <h1>When an agent moves money,<br />prove every decision.</h1>
        <p className="landing-sub">ClearCrew records each veto, ruling, and settlement as a hash-chained event — so any payout can be replayed, explained, and verified after the fact.</p>
        <div className="landing-cta">
          <Link className="cta-primary" to="/console">Enter the console</Link>
          <span className="cta-secondary is-gated" title="Gated — enabled in the live build">Run a live settlement · gated</span>
        </div>
      </section>

      <section className="landing-band">
        <div className="landing-col">
          <div className="section-kicker">The problem</div>
          <h2>Autonomous agents move money with no auditable trail.</h2>
          <p>When an AI approves or rejects a payout, the reasoning evaporates. There is nothing to replay, nothing to show a regulator, nothing to prove it was fair.</p>
        </div>
        <div className="landing-col">
          <div className="section-kicker">What ClearCrew is</div>
          <h2>Five specialist agents, one append-only record.</h2>
          <p>Intake, compliance, treasury, orchestration, and settlement each write to a hash-chained event log. A replay engine folds the log back into state; Verasettle executes only what was approved.</p>
        </div>
      </section>

      <section className="landing-proof">
        <div className="section-kicker">The guarantee</div>
        <ol className="proof-ladder">
          <li><b>Recorded</b><span>every decision is an event</span></li>
          <li><b>Replayable</b><span>state is folded from the log, not stored</span></li>
          <li><b>Verifiable</b><span>the hash chain checks itself</span></li>
          <li><b>Anchored</b><span>the record can be committed on-chain</span></li>
        </ol>
        <div className="landing-foot-cta">
          <Link className="cta-primary" to="/console">Open the evidence console</Link>
        </div>
      </section>

      <section className="landing-faq" aria-labelledby="faq-title">
        <div className="landing-faq-intro">
          <div className="section-kicker">Common questions</div>
          <h2 id="faq-title">A trail you can inspect without taking anyone’s word for it.</h2>
          <p>ClearCrew makes the record the source of truth—not a post-hoc summary.</p>
        </div>
        <div className="faq-list">
          {faqs.map(([question, answer], index) => (
            <details className="faq-item" key={question} open={index === 0}>
              <summary>{question}<span aria-hidden="true" /></summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="landing-final-cta">
        <div className="section-kicker">Start with the record</div>
        <h2>Make every autonomous payout explainable.</h2>
        <p>Open a recorded run, replay the state, and see precisely what cleared the settlement.</p>
        <Link className="cta-primary cta-primary-light" to="/console">Explore ClearCrew</Link>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer-brand"><span>ClearCrew</span><small>by Verasettle</small></div>
        <p>Built for autonomous systems that need a durable record.</p>
        <Link to="/console">Evidence console <span aria-hidden="true">→</span></Link>
      </footer>
    </main>
  )
}
