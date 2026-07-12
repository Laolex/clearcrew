import { useCallback, useEffect, useState } from 'react'
import { ChainIntegrity } from './components/ChainIntegrity'
import { EventRow } from './components/EventRow'
import { ActorChip, SectionLabel } from './components/Primitives'
import { api, type RunEvents } from './lib/api'
import type { RunDetail, RunSummary } from './lib/domain'
import { C, MONO, SANS } from './lib/tokens'

export default function App() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [trail, setTrail] = useState<RunEvents | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [cursor, setCursor] = useState(0)
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

  useEffect(() => {
    if (!active) return
    setExpanded(null)
    setCursor(0)
    Promise.all([api.run(active), api.events(active)])
      .then(([d, t]) => {
        setDetail(d)
        setTrail(t)
      })
      .catch((e: Error) => setError(e.message))
  }, [active])

  // Stepping the trail is keyboard-first, not an afterthought.
  const onKey = useCallback(
    (e: KeyboardEvent) => {
      if (!trail) return
      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault()
        setCursor((c) => Math.min(c + 1, trail.events.length - 1))
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        e.preventDefault()
        setCursor((c) => Math.max(c - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        setExpanded((x) => (x === cursor ? null : cursor))
      } else if (e.key === 'Escape') {
        setExpanded(null)
      }
    },
    [trail, cursor],
  )

  useEffect(() => {
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onKey])

  const untrustedFrom = trail?.untrusted_from ?? null

  // What the copy says has to be a fact about the events on screen, not a claim
  // about the product. The runs directory holds both society runs and the
  // single-agent baseline they are graded against; those are different stories
  // and must not be narrated with the same sentence.
  const actors = trail ? [...new Set(trail.events.map((e) => e.actor))] : []
  const isBaseline = actors.includes('monolith') && !actors.includes('compliance')
  const disputes = trail?.events.filter((e) => e.type === 'dispute.resolved').length ?? 0
  const vetoes = trail?.events.filter((e) => e.type === 'compliance.reviewed').length ?? 0

  return (
    <div style={{ background: C.bg.base, minHeight: '100vh', padding: '40px 48px' }}>
      <header style={{ marginBottom: '36px' }}>
        <div
          style={{
            fontFamily: MONO,
            fontSize: '10px',
            color: C.text.ghost,
            letterSpacing: '0.18em',
            marginBottom: '10px',
          }}
        >
          CLEARCREW
        </div>
        <h1
          style={{
            fontFamily: SANS,
            fontSize: '28px',
            fontWeight: 500,
            color: C.text.primary,
            margin: 0,
          }}
        >
          Payout Resolution Log
        </h1>
        <p
          style={{
            fontFamily: SANS,
            fontSize: '13px',
            color: C.text.muted,
            marginTop: '8px',
            maxWidth: '660px',
            lineHeight: 1.6,
          }}
        >
          {!trail
            ? 'Loading a recorded run…'
            : isBaseline
              ? 'This run is the single-agent baseline. One model decides alone — no specialists, no veto, nothing to negotiate. It is the control the society is graded against, shown here so the comparison is inspectable rather than asserted.'
              : `${actors.length} actors wrote to this log. Every judgment below is a recorded event committing to the hash of the one before it.`}
        </p>

        {/* Who actually spoke — read off the log, not off the pitch. */}
        {trail && (
          <div style={{ display: 'flex', gap: '6px', marginTop: '14px', flexWrap: 'wrap' }}>
            {actors.map((a) => (
              <ActorChip key={a} actor={a} />
            ))}
            {isBaseline && (
              <span
                style={{
                  fontFamily: MONO,
                  fontSize: '10px',
                  color: C.state.hypothetical,
                  border: `1px dashed ${C.state.hypothetical}`,
                  borderRadius: '3px',
                  padding: '3px 9px',
                  letterSpacing: '0.1em',
                }}
              >
                BASELINE · NOT THE SOCIETY
              </span>
            )}
          </div>
        )}
      </header>

      {error && (
        <div
          style={{
            background: '#280A0A',
            border: `1px solid #4A1414`,
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

      {/* Run selector — recorded runs, named by their file on disk. */}
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

      {/* Verification, as a checked result. */}
      {detail && (
        <div style={{ marginBottom: '28px', maxWidth: '720px' }}>
          <ChainIntegrity v={detail.chain} />
        </div>
      )}

      {/* The counts are context, not the hero. */}
      {detail && (
        <div style={{ display: 'flex', gap: '32px', marginBottom: '32px' }}>
          {[
            ['payouts', detail.payouts.length],
            ['approved', detail.payouts.filter((p) => p.status === 'approved').length],
            ['rejected', detail.payouts.filter((p) => p.status === 'rejected').length],
            ['settled', detail.payouts.filter((p) => p.status === 'settled').length],
            ['vetoes', vetoes],
            ['disputes resolved', disputes],
            ['events', detail.total_events],
          ].map(([k, v]) => (
            <div key={String(k)}>
              <div style={{ fontFamily: MONO, fontSize: '16px', color: C.text.primary }}>{v}</div>
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: '10px',
                  color: C.text.ghost,
                  letterSpacing: '0.1em',
                  marginTop: '2px',
                }}
              >
                {String(k).toUpperCase()}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* The trail gets the visual budget. */}
      <SectionLabel>
        Event trail {trail ? `· ${trail.events.length} events` : ''}
      </SectionLabel>
      <div
        style={{
          background: C.bg.surface,
          border: `1px solid ${C.border.hairline}`,
          borderRadius: '4px',
          overflow: 'hidden',
        }}
      >
        {trail?.events.map((e, i) => (
          <EventRow
            key={e.id}
            event={e}
            index={i}
            expanded={expanded === i}
            selected={cursor === i}
            untrusted={untrustedFrom !== null && i >= untrustedFrom}
            onToggle={() => {
              setCursor(i)
              setExpanded((x) => (x === i ? null : i))
            }}
          />
        ))}
        {!trail && (
          <div style={{ padding: '24px', fontFamily: MONO, fontSize: '12px', color: C.text.muted }}>
            loading recorded events…
          </div>
        )}
      </div>

      <footer
        style={{
          fontFamily: MONO,
          fontSize: '10px',
          color: C.text.ghost,
          marginTop: '20px',
          letterSpacing: '0.06em',
        }}
      >
        ↑↓ navigate · Enter expand · Esc collapse
      </footer>
    </div>
  )
}
