import type { ClearEvent } from '../lib/domain'
import { extras, isConflict, judgment, prose } from '../lib/payload'
import { C, MONO, SANS } from '../lib/tokens'
import { ActorChip, HashPill } from './Primitives'

const TYPE_COLOR: Record<string, string> = {
  'payout.approved': C.state.approved,
  'payout.settled': C.state.approved,
  'settlement.confirmed': C.state.approved,
  'payout.rejected': C.state.rejected,
  'policy.blocked': C.state.rejected,
  'compliance.reviewed': C.state.vetoed,
  'reconciliation.flagged': C.state.vetoed,
  'dispute.resolved': C.state.hypothetical,
  'treasury.decided': C.state.held,
}

// A judgment word is coloured by what it means, never by who said it.
const JUDGMENT_COLOR: Record<string, string> = {
  veto: C.state.vetoed,
  uphold_veto: C.state.vetoed,
  enforce_ledger: C.state.vetoed,
  reject: C.state.rejected,
  approve: C.state.approved,
  clear: C.state.approved,
  pay_now: C.state.approved,
  high: C.state.rejected,
  medium: C.state.vetoed,
  low: C.text.muted,
}

function hhmmss(ts: number): string {
  const d = new Date(ts * 1000)
  const p = (n: number, w = 2) => String(n).padStart(w, '0')
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`
}

export function EventRow({
  event,
  index,
  expanded,
  untrusted = false,
  selected = false,
  onToggle,
  onOpenSubject,
}: {
  event: ClearEvent
  index: number
  expanded: boolean
  untrusted?: boolean
  selected?: boolean
  onToggle: () => void
  onOpenSubject?: (subject: string) => void
}) {
  const text = prose(event)
  const verdict = judgment(event)
  const rest = extras(event)
  const conflict = isConflict(event)
  const typeColor = TYPE_COLOR[event.type] ?? C.text.secondary
  const vColor = verdict ? (JUDGMENT_COLOR[verdict.label] ?? C.text.secondary) : C.text.secondary

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={expanded}
      onClick={onToggle}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onToggle()
        }
      }}
      style={{
        borderBottom: `1px solid ${C.border.hairline}`,
        background: untrusted
          ? '#FBEDEC'
          : selected
            ? C.bg.elevated
            : // A disagreement is lifted off the surface of the log so the eye
              // lands on it without scanning every row for it.
              conflict
              ? '#FAF3E6'
              : 'transparent',
        borderLeft: untrusted
          ? `2px solid ${C.state.broken}`
          : conflict
            ? `2px solid ${C.state.vetoed}`
            : selected
              ? `2px solid ${C.border.strong}`
              : '2px solid transparent',
        cursor: 'pointer',
        outline: 'none',
      }}
      onFocus={(e) => {
        e.currentTarget.style.boxShadow = 'inset 0 0 0 1px #4A9CC4'
      }}
      onBlur={(e) => {
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', padding: '9px 14px', gap: '14px' }}>
        <span
          style={{
            fontFamily: MONO,
            fontSize: '10px',
            color: C.text.ghost,
            width: '32px',
            flexShrink: 0,
            textAlign: 'right',
          }}
        >
          {String(index).padStart(3, '0')}
        </span>

        <span style={{ fontFamily: MONO, fontSize: '11px', color: C.text.muted, flexShrink: 0 }}>
          {hhmmss(event.ts)}
        </span>

        <span style={{ fontFamily: MONO, fontSize: '12px', color: typeColor, width: '186px', flexShrink: 0 }}>
          {event.type}
        </span>

        <span style={{ width: '146px', flexShrink: 0 }}>
          <ActorChip actor={event.actor} />
        </span>

        {/* The subject is the way into the decision — "batch" is not a payout,
            so it is not a link. */}
        {event.subject === 'batch' || !onOpenSubject ? (
          <span
            style={{
              fontFamily: MONO,
              fontSize: '11px',
              color: C.text.muted,
              width: '76px',
              flexShrink: 0,
            }}
          >
            {event.subject}
          </span>
        ) : (
          <button
            onClick={(ev) => {
              ev.stopPropagation()
              onOpenSubject(event.subject)
            }}
            style={{
              fontFamily: MONO,
              fontSize: '11px',
              color: C.text.secondary,
              width: '76px',
              flexShrink: 0,
              textAlign: 'left',
              background: 'transparent',
              border: 'none',
              borderBottom: `1px dotted ${C.border.strong}`,
              padding: 0,
              cursor: 'pointer',
            }}
            title="Open the full decision for this payout"
          >
            {event.subject}
          </button>
        )}

        {/* The judgment word, on the row — you should not have to expand to see
            that this is where an agent vetoed something. */}
        <span style={{ width: '108px', flexShrink: 0 }}>
          {verdict && (
            <span
              style={{
                fontFamily: MONO,
                fontSize: '10px',
                color: vColor,
                border: `1px solid ${vColor}44`,
                background: `${vColor}14`,
                borderRadius: '3px',
                padding: '2px 6px',
                letterSpacing: '0.06em',
              }}
            >
              {verdict.label}
            </span>
          )}
        </span>

        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          <HashPill hash={event.prev_hash} dim />
          <span style={{ color: C.text.ghost, fontSize: '10px' }}>›</span>
          <HashPill hash={event.event_hash} />
        </span>

        <span style={{ flex: 1 }} />

        {untrusted && (
          <span style={{ fontFamily: MONO, fontSize: '9px', color: C.state.broken, letterSpacing: '0.1em' }}>
            UNTRUSTED
          </span>
        )}

        <span style={{ color: expanded ? C.text.secondary : C.text.ghost, fontSize: '10px' }}>
          {expanded ? '▼' : '▶'}
        </span>
      </div>

      {expanded && (
        <div style={{ padding: '2px 14px 16px 60px' }}>
          {text && (
            <div style={{ maxWidth: '900px', marginBottom: rest.length ? '12px' : 0 }}>
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: '9px',
                  color: C.text.ghost,
                  letterSpacing: '0.12em',
                  marginBottom: '5px',
                }}
              >
                {event.type === 'audit.explained' ? 'EXPLANATION' : 'REASON'}
              </div>
              <div
                style={{
                  fontFamily: SANS,
                  fontSize: '13px',
                  color: untrusted ? C.state.rejected : C.text.primary,
                  lineHeight: 1.6,
                }}
              >
                {text}
              </div>
            </div>
          )}

          {rest.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
              {rest.map(([k, v]) => (
                <div key={k} style={{ maxWidth: '420px' }}>
                  <div
                    style={{
                      fontFamily: MONO,
                      fontSize: '9px',
                      color: C.text.ghost,
                      letterSpacing: '0.12em',
                      marginBottom: '3px',
                    }}
                  >
                    {k.toUpperCase()}
                  </div>
                  <div
                    style={{
                      fontFamily: MONO,
                      fontSize: '11px',
                      color: C.text.secondary,
                      wordBreak: 'break-all',
                    }}
                  >
                    {v}
                  </div>
                </div>
              ))}
            </div>
          )}

          {!text && rest.length === 0 && (
            <div style={{ fontFamily: SANS, fontSize: '12px', color: C.text.muted }}>
              No judgment recorded — this event carries structure, not reasoning.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
