import { Link } from 'react-router-dom'

export function Landing() {
  return (
    <main className="landing">
      <section className="landing-hero">
        <p className="eyebrow">ClearCrew</p>
        <h1>Proof layer for autonomous payouts</h1>
        <p className="landing-sub">Every decision an agent makes is a hash-chained event you can replay, explain, and verify.</p>
        <div className="landing-cta">
          <Link className="cta-primary" to="/console">Enter the console</Link>
          <span className="cta-secondary is-gated" aria-disabled="true">Run a live settlement · gated</span>
        </div>
      </section>
    </main>
  )
}
