import { useState } from 'react'
import type { Actor } from '../lib/domain'
import { ACTOR_META, GENESIS_HASH } from '../lib/domain'
import { C, MONO, SANS } from '../lib/tokens'

export function midTruncate(hash: string, head = 4, tail = 4): string {
  if (hash === GENESIS_HASH) return 'genesis'
  if (hash.length <= head + tail + 1) return hash
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`
}

/** A hash is the load-bearing artifact here, so it is copyable, never decorative. */
export function HashPill({ hash, dim = false }: { hash?: string; dim?: boolean }) {
  const [copied, setCopied] = useState(false)
  // Early archived runs are valid historical evidence, but they predate the
  // hash-chain format. A missing hash must be legible, never a React crash.
  if (!hash) {
    return (
      <span
        title="This recorded run predates hash chaining"
        style={{
          fontFamily: MONO,
          fontSize: '10px',
          color: C.text.ghost,
          border: `1px dashed ${C.border.hairline}`,
          borderRadius: '3px',
          padding: '2px 8px',
          letterSpacing: '0.04em',
          whiteSpace: 'nowrap',
        }}
      >
        unhashed
      </span>
    )
  }
  const genesis = hash === GENESIS_HASH

  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        navigator.clipboard?.writeText(hash).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1400)
        })
      }}
      title={genesis ? `Genesis — no parent (${hash})` : `Copy: ${hash}`}
      style={{
        fontFamily: MONO,
        fontSize: '11px',
        background: C.bg.surface,
        color: dim ? C.text.ghost : C.text.muted,
        border: `1px solid ${C.border.hairline}`,
        borderRadius: '3px',
        padding: '2px 8px',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        cursor: 'pointer',
        letterSpacing: '0.04em',
        whiteSpace: 'nowrap',
        transition: 'color 80ms, background 80ms, border-color 80ms',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = C.text.secondary
        e.currentTarget.style.background = C.bg.elevated
        e.currentTarget.style.borderColor = C.border.strong
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = dim ? C.text.ghost : C.text.muted
        e.currentTarget.style.background = C.bg.surface
        e.currentTarget.style.borderColor = C.border.hairline
      }}
      onFocus={(e) => {
        e.currentTarget.style.outline = 'none'
        e.currentTarget.style.boxShadow = '0 0 0 1px #4A9CC4'
      }}
      onBlur={(e) => {
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      <span>{midTruncate(hash)}</span>
      <span
        style={{
          fontSize: '9px',
          opacity: copied ? 1 : 0,
          color: copied ? C.state.approved : C.text.muted,
          transition: 'opacity 120ms',
        }}
      >
        ✓
      </span>
    </button>
  )
}

/** Ten actors can write to the log, not five. The chip must name all of them. */
export function ActorChip({ actor, size = 'sm' }: { actor: Actor; size?: 'sm' | 'md' }) {
  const m = ACTOR_META[actor]
  if (!m) {
    // An unknown actor is a data-integrity signal, not a styling problem — say so.
    return (
      <span style={{ fontFamily: MONO, fontSize: '11px', color: C.state.rejected }}>
        ?? {actor}
      </span>
    )
  }
  return (
    <span
      title={m.role}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        background: C.bg.surface,
        color: C.text.secondary,
        border: `1px solid ${C.border.hairline}`,
        borderRadius: '3px',
        padding: size === 'md' ? '4px 10px' : '2px 7px',
        fontSize: size === 'md' ? '12px' : '11px',
        fontFamily: SANS,
        fontWeight: 500,
        whiteSpace: 'nowrap',
      }}
    >
      <span style={{ fontFamily: MONO, fontSize: '9px', opacity: 0.65, letterSpacing: '0.06em' }}>
        {m.short}
      </span>
      {m.label}
    </span>
  )
}

/** A figure and what it counts. Never a "hero metric" — the number is the size
 *  it needs to be read, and no larger. */
export function Stat({
  value,
  label,
  tone,
}: {
  value: string | number
  label: string
  tone?: string
}) {
  return (
    <div>
      <div style={{ fontFamily: MONO, fontSize: '16px', color: tone ?? C.text.primary }}>{value}</div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: '10px',
          color: C.text.ghost,
          letterSpacing: '0.1em',
          marginTop: '2px',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </div>
    </div>
  )
}

export function Panel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        background: C.bg.surface,
        border: `1px solid ${C.border.hairline}`,
        borderRadius: '4px',
        overflow: 'hidden',
      }}
    >
      {children}
    </div>
  )
}

export function Loading({ error }: { error?: string | null }) {
  return (
    <div
      style={{
        padding: '24px',
        fontFamily: MONO,
        fontSize: '12px',
        color: error ? C.state.rejected : C.text.muted,
      }}
    >
      {error ?? 'loading…'}
    </div>
  )
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
      <span
        style={{
          fontFamily: MONO,
          fontSize: '10px',
          color: C.text.ghost,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
        }}
      >
        {children}
      </span>
      <div style={{ flex: 1, height: '1px', background: C.border.hairline }} />
    </div>
  )
}
