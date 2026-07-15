import type { ClearEvent, EventType } from './domain'

// Payload keys differ by actor — the auditor writes `explanation`, compliance
// writes `verdict` + `policy_rule`, resolution writes `ruling` + `conditions`.
// Reading only `reason` silently hides most of what the log actually says.

/** The verbatim prose an actor recorded, whatever key it used. */
export function prose(e: ClearEvent): string | null {
  const p = e.payload ?? {}
  for (const k of ['reason', 'explanation'] as const) {
    const v = p[k]
    if (typeof v === 'string' && v.trim()) return v
  }
  return null
}

/** The single word that is this event's judgment, if it made one. */
export function judgment(e: ClearEvent): { label: string; key: string } | null {
  const p = e.payload ?? {}
  for (const k of ['verdict', 'ruling', 'action', 'risk_tier'] as const) {
    const v = p[k]
    if (typeof v === 'string' && v) return { label: v, key: k }
  }
  return null
}

/** Everything else worth showing, in a stable order, minus what is already shown. */
const SHOWN = new Set(['reason', 'explanation', 'verdict', 'ruling', 'action', 'risk_tier', 'payout_id'])

export function extras(e: ClearEvent): [string, string][] {
  const p = e.payload ?? {}
  return Object.entries(p)
    .filter(([k, v]) => !SHOWN.has(k) && v !== null && v !== undefined && v !== '')
    .map(([k, v]) => [k, Array.isArray(v) ? v.join(', ') : String(v)] as [string, string])
    .filter(([, v]) => v.length > 0)
}

/** Events where the society disagreed with itself. This is the thesis, so it
 *  must be findable structurally rather than by reading every row. */
const CONFLICT_TYPES: ReadonlySet<string> = new Set<EventType>([
  'compliance.reviewed',
  'dispute.resolved',
  'reconciliation.flagged',
  'policy.blocked',
])

export function isConflict(e: ClearEvent): boolean {
  if (!CONFLICT_TYPES.has(e.type)) return false
  // A clean compliance review is not a disagreement — only a veto is.
  if (e.type === 'compliance.reviewed') return e.payload?.verdict === 'veto'
  return true
}
