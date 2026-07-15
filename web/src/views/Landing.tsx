import { Link } from 'react-router-dom'

export function Landing() {
  return (
    <main className="landing">
      <header className="landing-topbar">
        <span className="landing-mark">Verasettle<span>.</span> <small>ClearCrew</small></span>
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
    </main>
  )
}
