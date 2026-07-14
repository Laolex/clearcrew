import { useCallback, useEffect, useState } from 'react'
import { ChainIntegrity } from '../components/ChainIntegrity'
import { EventRow } from '../components/EventRow'
import { ActorChip, Loading, Panel, SectionLabel, Stat } from '../components/Primitives'
import { api, type RunEvents } from '../lib/api'
import type { RunDetail } from '../lib/domain'
import { isConflict } from '../lib/payload'
import { C, MONO, SANS } from '../lib/tokens'

export function RunTrail({
  run,
  onOpenSubject,
}: {
  run: string
  onOpenSubject: (subject: string) => void
}) {
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [trail, setTrail] = useState<RunEvents | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [cursor, setCursor] = useState(0)
  const [onlyConflicts, setOnlyConflicts] = useState(false)
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setExpanded(null)
    setCursor(0)
    setDetail(null)
    setTrail(null)
    Promise.all([api.run(run), api.events(run)])
      .then(([d, t]) => {
        setDetail(d)
        setTrail(t)
      })
      .catch((e: Error) => setError(e.message))
  }, [run])

  const untrustedFrom = trail?.untrusted_from ?? null
  const actors = trail ? [...new Set(trail.events.map((e) => e.actor))] : []
  const isBaseline = actors.includes('monolith') && !actors.includes('compliance')
  const disputes = trail?.events.filter((e) => e.type === 'dispute.resolved').length ?? 0
  const vetoes = trail?.events.filter((e) => isConflict(e) && e.type === 'compliance.reviewed').length ?? 0

  const all = trail?.events ?? []
  const conflicts = all.filter(isConflict)
  const searched = query.trim().toLowerCase()
  const shown = (onlyConflicts ? conflicts : all).filter((e) =>
    !searched || [e.id, e.subject, e.type, e.actor].some((v) => v.toLowerCase().includes(searched)),
  )

  const onKey = useCallback(
    (e: KeyboardEvent) => {
      if (!shown.length) return
      if (e.key === 'ArrowDown' || e.key === 'j') {
        e.preventDefault()
        setCursor((c) => Math.min(c + 1, shown.length - 1))
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
    [shown.length, cursor],
  )

  useEffect(() => {
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onKey])

  if (!trail || !detail) return <Loading error={error} />

  return (
    <>
      {/* Who actually spoke — read off the log, not off the pitch. */}
      <div style={{ display: 'flex', gap: '6px', marginBottom: '10px', flexWrap: 'wrap' }}>
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

      <p
        style={{
          fontFamily: SANS,
          fontSize: '13px',
          color: C.text.muted,
          margin: '0 0 24px',
          maxWidth: '680px',
          lineHeight: 1.6,
        }}
      >
        {isBaseline
          ? 'This run is the single-agent baseline. One model decides alone — no specialists, no veto, nothing to negotiate. It is the control the society is graded against, shown here so the comparison is inspectable rather than asserted.'
          : `${actors.length} actors wrote to this log. Every judgment below is a recorded event committing to the hash of the one before it.`}
      </p>

      <div style={{ marginBottom: '26px', maxWidth: '720px' }}>
        <ChainIntegrity v={detail.chain} />
      </div>

      <div style={{ display: 'flex', gap: '32px', marginBottom: '30px', flexWrap: 'wrap' }}>
        <Stat value={detail.payouts.length} label="payouts" />
        <Stat value={detail.payouts.filter((p) => p.status === 'approved').length} label="approved" />
        <Stat value={detail.payouts.filter((p) => p.status === 'rejected').length} label="rejected" />
        <Stat value={detail.payouts.filter((p) => p.status === 'settled').length} label="settled" />
        <Stat value={vetoes} label="vetoes" tone={vetoes ? C.state.vetoed : undefined} />
        <Stat
          value={disputes}
          label="disputes resolved"
          tone={disputes ? C.state.hypothetical : undefined}
        />
        <Stat value={detail.total_events} label="events" />
      </div>

      <SectionLabel>Event trail</SectionLabel>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        {(
          [
            [false, `all events · ${all.length}`],
            [true, `disagreements only · ${conflicts.length}`],
          ] as const
        ).map(([v, label]) => (
          <button
            key={String(v)}
            onClick={() => {
              setOnlyConflicts(v)
              setCursor(0)
              setExpanded(null)
            }}
            style={{
              fontFamily: MONO,
              fontSize: '11px',
              background: onlyConflicts === v ? C.bg.elevated : 'transparent',
              color: onlyConflicts === v ? C.text.primary : C.text.muted,
              border: `1px solid ${onlyConflicts === v ? C.border.strong : C.border.hairline}`,
              borderRadius: '3px',
              padding: '5px 10px',
              cursor: 'pointer',
            }}
          >
            {label}
          </button>
        ))}
        {onlyConflicts && conflicts.length === 0 && (
          <span style={{ fontFamily: SANS, fontSize: '12px', color: C.text.muted }}>
            Nothing was contested in this run.
          </span>
        )}
        <input
          aria-label="Search events"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setCursor(0); setExpanded(null) }}
          placeholder="search id, actor, type"
          style={{ marginLeft: 'auto', fontFamily: MONO, fontSize: '11px', background: C.bg.surface, color: C.text.primary, border: `1px solid ${C.border.hairline}`, borderRadius: '3px', padding: '6px 9px', width: '190px' }}
        />
      </div>

      <Panel>
        {shown.map((e, i) => {
          // The event's real position in the chain, not its position in the
          // filtered view — a filtered row must still say where it truly sits.
          const trueIndex = all.indexOf(e)
          return (
            <EventRow
              key={e.id}
              event={e}
              index={trueIndex}
              expanded={expanded === i}
              selected={cursor === i}
              untrusted={untrustedFrom !== null && trueIndex >= untrustedFrom}
              onToggle={() => {
                setCursor(i)
                setExpanded((x) => (x === i ? null : i))
              }}
              onOpenSubject={onOpenSubject}
            />
          )
        })}
      </Panel>

      <div
        style={{
          fontFamily: MONO,
          fontSize: '10px',
          color: C.text.ghost,
          marginTop: '16px',
          letterSpacing: '0.06em',
        }}
      >
        ↑↓ navigate · Enter expand · Esc collapse · click a payout id for its full decision
      </div>
    </>
  )
}
