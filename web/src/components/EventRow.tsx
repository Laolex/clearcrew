import type { ClearEvent } from '../lib/domain'
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

function hhmmss(ts: number): string {
  const d = new Date(ts * 1000)
  const p = (n: number, w = 2) => String(n).padStart(w, '0')
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}.${p(d.getUTCMilliseconds(), 3)}`
}

/** One recorded judgment. The `reason` is the most valuable thing on the screen,
 *  so expanding a row surfaces it verbatim — never summarised, never truncated. */
export function EventRow({
  event,
  index,
  expanded,
  untrusted = false,
  selected = false,
  onToggle,
}: {
  event: ClearEvent
  index: number
  expanded: boolean
  untrusted?: boolean
  selected?: boolean
  onToggle: () => void
}) {
  const reason = typeof event.payload?.reason === 'string' ? event.payload.reason : null
  const action = typeof event.payload?.action === 'string' ? event.payload.action : null
  const typeColor = TYPE_COLOR[event.type] ?? C.text.secondary

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
        // Everything at or after a break is untrusted. That has to be visible on
        // the row itself, not only in a banner at the top of the page.
        background: untrusted ? '#1E0808' : selected ? C.bg.elevated : 'transparent',
        borderLeft: untrusted
          ? `2px solid ${C.state.broken}`
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

        <span
          style={{
            fontFamily: MONO,
            fontSize: '12px',
            color: typeColor,
            width: '190px',
            flexShrink: 0,
          }}
        >
          {event.type}
        </span>

        <span style={{ width: '150px', flexShrink: 0 }}>
          <ActorChip actor={event.actor} />
        </span>

        <span
          style={{
            fontFamily: MONO,
            fontSize: '11px',
            color: C.text.secondary,
            width: '80px',
            flexShrink: 0,
          }}
        >
          {event.subject}
        </span>

        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
          <HashPill hash={event.prev_hash} dim />
          <span style={{ color: C.text.ghost, fontSize: '10px' }}>›</span>
          <HashPill hash={event.event_hash} />
        </span>

        <span style={{ flex: 1 }} />

        {untrusted && (
          <span
            style={{
              fontFamily: MONO,
              fontSize: '9px',
              color: C.state.broken,
              letterSpacing: '0.1em',
            }}
          >
            UNTRUSTED
          </span>
        )}

        <span style={{ color: expanded ? C.text.secondary : C.text.ghost, fontSize: '10px' }}>
          {expanded ? '▼' : '▶'}
        </span>
      </div>

      {expanded && (
        <div style={{ padding: '0 14px 14px 60px', display: 'flex', gap: '28px' }}>
          {action && (
            <div>
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: '9px',
                  color: C.text.ghost,
                  letterSpacing: '0.12em',
                  marginBottom: '4px',
                }}
              >
                ACTION
              </div>
              <div style={{ fontFamily: MONO, fontSize: '12px', color: C.text.secondary }}>
                {action}
              </div>
            </div>
          )}
          {reason && (
            <div style={{ flex: 1 }}>
              <div
                style={{
                  fontFamily: MONO,
                  fontSize: '9px',
                  color: C.text.ghost,
                  letterSpacing: '0.12em',
                  marginBottom: '4px',
                }}
              >
                REASON
              </div>
              <div
                style={{
                  fontFamily: SANS,
                  fontSize: '13px',
                  color: untrusted ? C.state.rejected : C.text.primary,
                  lineHeight: 1.55,
                }}
              >
                {reason}
              </div>
            </div>
          )}
          {!reason && !action && (
            <div style={{ fontFamily: SANS, fontSize: '12px', color: C.text.muted }}>
              No reason recorded — this event carries structure, not judgment.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
