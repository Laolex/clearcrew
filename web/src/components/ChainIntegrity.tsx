import type { ChainVerification } from '../lib/domain'
import { BREAK_COPY, breakCause, chainState } from '../lib/domain'
import { C, MONO, SANS } from '../lib/tokens'

/** Verification is shown as a checked result, never asserted as a badge.
 *  The three states must not be mistakable for one another — a pre-hash run
 *  is not a verified one, and a fork is not a tamper. */
export function ChainIntegrity({ v, compact = false }: { v?: ChainVerification; compact?: boolean }) {
  const state = chainState(v)
  const cause = v && state === 'broken' ? breakCause(v) : null

  const skin = {
    verified: { fg: C.state.approved, bg: '#142819', bd: '#1E4028' },
    unverified: { fg: C.text.muted, bg: C.bg.surface, bd: C.border.hairline },
    broken: { fg: C.state.rejected, bg: '#280A0A', bd: '#4A1414' },
  }[state]

  const headline =
    state === 'verified'
      ? 'chain verified'
      : state === 'unverified'
        ? 'unverified · pre-hash'
        : cause
          ? BREAK_COPY[cause].label
          : 'chain broken'

  const detail =
    state === 'verified'
      ? `${v?.events ?? 0} events · every event commits to the one before it`
      : state === 'unverified'
        ? 'This run predates hashing. Hashes were never written, so nothing can be verified.'
        : cause
          ? BREAK_COPY[cause].detail
          : ''

  if (compact) {
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '7px',
          fontFamily: MONO,
          fontSize: '11px',
          color: skin.fg,
        }}
      >
        <span
          style={{
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            background: state === 'unverified' ? 'transparent' : skin.fg,
            border: state === 'unverified' ? `1.5px solid ${C.text.ghost}` : 'none',
            flexShrink: 0,
          }}
        />
        {headline}
        {v?.hashed && (
          <span style={{ color: C.text.ghost }}>
            · {v.events} events
            {v.broken_at !== null && v.broken_at !== undefined && ` · breaks at ${v.broken_at}`}
          </span>
        )}
      </span>
    )
  }

  return (
    <div
      style={{
        background: skin.bg,
        border: `1px solid ${skin.bd}`,
        borderRadius: '4px',
        padding: '14px 16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span
          style={{
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            background: state === 'unverified' ? 'transparent' : skin.fg,
            border: state === 'unverified' ? `1.5px solid ${C.text.ghost}` : 'none',
            flexShrink: 0,
          }}
        />
        <span style={{ fontFamily: MONO, fontSize: '12px', color: skin.fg, letterSpacing: '0.02em' }}>
          {headline}
        </span>
        {v && v.broken_at !== null && v.broken_at !== undefined && (
          <span style={{ fontFamily: MONO, fontSize: '12px', color: skin.fg, opacity: 0.8 }}>
            at index {v.broken_at} · events {v.broken_at}+ untrusted
          </span>
        )}
      </div>
      <div
        style={{
          fontFamily: SANS,
          fontSize: '12px',
          color: state === 'broken' ? C.text.secondary : C.text.muted,
          marginTop: '6px',
          lineHeight: 1.5,
        }}
      >
        {detail}
      </div>
    </div>
  )
}
