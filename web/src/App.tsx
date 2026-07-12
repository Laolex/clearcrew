import { useEffect, useState } from 'react'
import { DecisionDetail } from './components/DecisionDetail'
import { SectionLabel } from './components/Primitives'
import { api } from './lib/api'
import type { RunSummary } from './lib/domain'
import { C, MONO, SANS } from './lib/tokens'
import { Analytics } from './views/Analytics'
import { Counterfactual } from './views/Counterfactual'
import { Evidence } from './views/Evidence'
import { Failures } from './views/Failures'
import { Overview } from './views/Overview'
import { Policy } from './views/Policy'
import { RunTrail } from './views/RunTrail'

const VIEWS = [
  ['overview', 'Overview', 'Everything recorded, across every run'],
  ['run', 'Run', 'One batch, event by event'],
  ['failures', 'Failures', 'Vetoes, disputes, and where the society was wrong'],
  ['evidence', 'Evidence', 'Verify the chain yourself, then break it'],
  ['counterfactual', 'Counterfactual', 'What a different rule would have decided'],
  ['analytics', 'Benchmark', 'The society against the single agent'],
  ['policy', 'Policy', 'The rules in force'],
] as const

type ViewKey = (typeof VIEWS)[number][0]

export default function App() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [view, setView] = useState<ViewKey>('overview')
  const [subject, setSubject] = useState<{ run: string; id: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .runs()
      .then(({ runs }) => {
        setRuns(runs)
        // Default to the newest run that actually exercised the society. The
        // monolith baseline runs are recorded in the same directory, and opening
        // on one of those would show a batch with no disagreement in it at all.
        const society = runs.filter((r) => !r.name.includes('mono'))
        const pick = (society.length ? society : runs).at(-1)
        if (pick) setActive(pick.name)
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  const meta = VIEWS.find((v) => v[0] === view)!
  // Only the views that read one run need the run selector on screen.
  const runScoped = view === 'run' || view === 'evidence' || view === 'counterfactual'

  return (
    <div style={{ background: C.bg.base, minHeight: '100vh', padding: '36px 48px 80px' }}>
      <header style={{ marginBottom: '24px' }}>
        <div
          style={{
            fontFamily: MONO,
            fontSize: '10px',
            color: C.text.ghost,
            letterSpacing: '0.18em',
            marginBottom: '10px',
          }}
        >
          CLEARCREW · TRUST LAYER FOR AUTONOMOUS PAYOUTS
        </div>
        <h1 style={{ fontFamily: SANS, fontSize: '26px', fontWeight: 500, color: C.text.primary, margin: 0 }}>
          {meta[1]}
        </h1>
        <p style={{ fontFamily: SANS, fontSize: '13px', color: C.text.muted, margin: '6px 0 0' }}>
          {meta[2]}
        </p>
      </header>

      <nav
        style={{
          display: 'flex',
          gap: '2px',
          marginBottom: '30px',
          borderBottom: `1px solid ${C.border.hairline}`,
          flexWrap: 'wrap',
        }}
      >
        {VIEWS.map(([key, label]) => {
          const on = key === view
          return (
            <button
              key={key}
              onClick={() => setView(key)}
              style={{
                fontFamily: MONO,
                fontSize: '12px',
                background: 'transparent',
                color: on ? C.text.primary : C.text.muted,
                border: 'none',
                borderBottom: `2px solid ${on ? C.text.primary : 'transparent'}`,
                padding: '9px 14px',
                cursor: 'pointer',
                marginBottom: '-1px',
              }}
            >
              {label}
            </button>
          )
        })}
      </nav>

      {error && (
        <div
          style={{
            background: '#280A0A',
            border: '1px solid #4A1414',
            borderRadius: '4px',
            padding: '12px 14px',
            fontFamily: MONO,
            fontSize: '12px',
            color: C.state.rejected,
            marginBottom: '24px',
          }}
        >
          {error}
        </div>
      )}

      {runScoped && (
        <div style={{ marginBottom: '28px' }}>
          <SectionLabel>Recorded runs</SectionLabel>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {runs.map((r) => (
              <button
                key={r.name}
                onClick={() => setActive(r.name)}
                style={{
                  fontFamily: MONO,
                  fontSize: '11px',
                  background: r.name === active ? C.bg.elevated : C.bg.surface,
                  color: r.name === active ? C.text.primary : C.text.muted,
                  border: `1px solid ${r.name === active ? C.border.strong : C.border.hairline}`,
                  borderRadius: '3px',
                  padding: '6px 10px',
                  cursor: 'pointer',
                }}
              >
                {r.stamp} · n={r.n}
              </button>
            ))}
          </div>
        </div>
      )}

      {view === 'overview' && (
        <Overview onOpen={(run, id) => setSubject({ run, id })} />
      )}
      {view === 'run' && active && (
        <RunTrail run={active} onOpenSubject={(id) => setSubject({ run: active, id })} />
      )}
      {view === 'failures' && <Failures onOpen={(run, id) => setSubject({ run, id })} />}
      {view === 'evidence' && <Evidence run={active} />}
      {view === 'counterfactual' && <Counterfactual run={active} />}
      {view === 'analytics' && <Analytics />}
      {view === 'policy' && <Policy />}

      {subject && (
        <DecisionDetail
          run={subject.run}
          subject={subject.id}
          onClose={() => setSubject(null)}
        />
      )}
    </div>
  )
}
