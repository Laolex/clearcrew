import { useEffect, useState } from 'react'
import { DecisionDetail } from './components/DecisionDetail'
import { api } from './lib/api'
import type { RunSummary } from './lib/domain'
import { Analytics } from './views/Analytics'
import { Counterfactual } from './views/Counterfactual'
import { Evidence } from './views/Evidence'
import { Failures } from './views/Failures'
import { JudgeWorkspace } from './views/JudgeWorkspace'
import { Overview } from './views/Overview'
import { Policy } from './views/Policy'
import { RunTrail } from './views/RunTrail'

const VIEWS = [
  ['overview', 'Overview', 'Recorded operations at a glance'],
  ['run', 'Run trail', 'Inspect one recorded batch'],
  ['failures', 'Exceptions', 'Vetoes, disputes, and misses'],
  ['evidence', 'Evidence', 'Verify and export the record'],
  ['counterfactual', 'Counterfactual', 'Test a policy without changing history'],
  ['analytics', 'Benchmark', 'Compare the society to a single agent'],
  ['policy', 'Policy', 'Rules in force'],
  ['demo', 'Try it', 'Create a payout and inspect its isolated evidence'],
] as const

type ViewKey = (typeof VIEWS)[number][0]

function SettledMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id="settled-gradient" x1="10" y1="8" x2="54" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#5EEAD4" />
          <stop offset=".55" stopColor="#2DD4BF" />
          <stop offset="1" stopColor="#0D9488" />
        </linearGradient>
      </defs>
      <path d="M15 24 30 42 52 11" stroke="url(#settled-gradient)" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="31" cy="17" r="4.8" fill="#2DD4BF" />
      <path d="M36.1 48.7a7.5 7.5 0 1 1-12.2 0" stroke="url(#settled-gradient)" strokeWidth="3.5" strokeLinecap="round" />
    </svg>
  )
}

export default function App() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [view, setView] = useState<ViewKey>('overview')
  const [subject, setSubject] = useState<{ run: string; id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.runs().then(({ runs: recorded }) => {
      setRuns(recorded)
      const society = recorded.filter((r) => !r.name.includes('mono'))
      const pick = (society.length ? society : recorded).at(-1)
      if (pick) setActive(pick.name)
    }).catch((e: Error) => setError(e.message))
  }, [])

  const meta = VIEWS.find((item) => item[0] === view)!
  const runScoped = view === 'run' || view === 'evidence' || view === 'counterfactual'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <SettledMark />
          <div><strong>Verasettle<span>.</span></strong><small>ClearCrew audit</small></div>
        </div>
        <div className="sidebar-label">Audit workspace</div>
        <nav className="side-nav" aria-label="ClearCrew sections">
          {VIEWS.map(([key, label]) => (
            <button key={key} className={key === view ? 'active' : ''} onClick={() => setView(key)}>
              {label}
            </button>
          ))}
        </nav>
        <div className="sidebar-proof"><span /> Recorded evidence<br />read-only replay</div>
      </aside>

      <main className="app-main">
        <header className="topbar">
          <div>
            <p className="eyebrow">ClearCrew / audit trail</p>
            <h1>{meta[1]}</h1>
            <p className="page-description">{meta[2]}</p>
          </div>
          <div className="topbar-proof"><span>Evidence mode</span><b>Append-only</b></div>
        </header>

        {error && <div className="app-error" role="alert">Unable to load recorded runs: {error}</div>}

        {runScoped && (
          <section className="run-switcher" aria-label="Recorded runs">
            <div><p className="eyebrow">Recorded run</p><strong>{active ? active.replace('events-', '').replace('.jsonl', '') : 'Loading archive…'}</strong></div>
            <div className="run-options">
              {runs.map((r) => <button key={r.name} className={r.name === active ? 'selected' : ''} onClick={() => setActive(r.name)}>{r.stamp} <span>n={r.n}</span></button>)}
            </div>
          </section>
        )}

        <div className="page-content">
          {view === 'demo' && <JudgeWorkspace />}
          {view === 'overview' && <Overview onOpen={(run, id) => setSubject({ run, id })} />}
          {view === 'run' && active && <RunTrail run={active} onOpenSubject={(id) => setSubject({ run: active, id })} />}
          {view === 'failures' && <Failures onOpen={(run, id) => setSubject({ run, id })} />}
          {view === 'evidence' && <Evidence run={active} />}
          {view === 'counterfactual' && <Counterfactual run={active} />}
          {view === 'analytics' && <Analytics />}
          {view === 'policy' && <Policy />}
        </div>
      </main>
      {subject && <DecisionDetail run={subject.run} subject={subject.id} onClose={() => setSubject(null)} />}
    </div>
  )
}
