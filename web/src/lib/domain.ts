// The vocabulary of the event log — derived from the recorded runs in src/runs,
// not from a design mock. If an actor or type appears here it appears on disk.

export type Actor =
  | 'orchestrator'
  | 'intake'
  | 'compliance'
  | 'treasury'
  | 'resolution'
  | 'auditor'
  | 'verasettle'
  | 'anchor'
  | 'monolith'
  | 'policy'

export type EventType =
  | 'batch.received'
  | 'policy.enacted'
  | 'policy.proposed'
  | 'policy.blocked'
  | 'payout.proposed'
  | 'intake.classified'
  | 'compliance.fast_tracked'
  | 'compliance.reviewed'
  | 'treasury.decided'
  | 'reconciliation.flagged'
  | 'dispute.resolved'
  | 'payout.approved'
  | 'payout.rejected'
  | 'audit.explained'
  | 'settlement.requested'
  | 'settlement.confirmed'
  | 'payout.settled'
  | 'chain.anchored'
  | 'batch.completed'

/** An event exactly as it sits on a line of runs/events-*.jsonl. */
export interface ClearEvent {
  id: string
  ts: number
  type: EventType
  subject: string // a payout id, or the literal "batch"
  actor: Actor
  payload: Record<string, unknown> & { reason?: string; action?: string }
  prev_hash: string
  event_hash: string
  t_offset?: number // added by /explain
}

/** The exact shape returned by events.verify_chain. */
export interface ChainVerification {
  hashed: boolean // false = a pre-hash run; hashes were never written
  verified: boolean
  events: number
  broken_at: number | null // first index that fails a linear walk
  forks: unknown[] // two events claim the same prev_hash — history branched
  orphans: unknown[] // an event's prev_hash names nothing — something was dropped
}

/** Why a chain failed. These are not the same failure and must not read alike. */
export type BreakCause = 'fork' | 'orphan' | 'tamper'

export function breakCause(v: ChainVerification): BreakCause | null {
  if (v.verified) return null
  if (v.forks.length > 0) return 'fork'
  if (v.orphans.length > 0) return 'orphan'
  return 'tamper' // content no longer matches its own hash
}

export const BREAK_COPY: Record<BreakCause, { label: string; detail: string }> = {
  fork: {
    label: 'chain forked',
    detail: 'Two events claim the same parent. History was not edited — it was branched by a second writer.',
  },
  orphan: {
    label: 'chain orphaned',
    detail: 'An event names a parent that is not in the log. Something upstream was dropped.',
  },
  tamper: {
    label: 'chain broken',
    detail: 'An event no longer matches its own hash. The content was altered after it was written.',
  },
}

export type PayoutStatus = 'pending' | 'approved' | 'rejected' | 'settled'

export interface Payout {
  id: string
  status: PayoutStatus
  events: number
  disputed: boolean
  proposed: string | null
  blocked_rule: string | null
  amount?: number
  currency?: string
  corridor?: string
  recipient_age_days?: number
  memo?: string
  expected?: string
  miss?: boolean
}

export interface RunSummary {
  name: string
  stamp: string
  n: number
  results: Record<string, unknown> | null
}

export interface RunDetail {
  run: string
  t0: number
  total_events: number
  chain: ChainVerification
  payouts: Payout[]
}

export interface Explain {
  subject: string
  payout: Record<string, unknown> | null
  verification: ChainVerification
  chain: ClearEvent[]
}

export const GENESIS_HASH = '0'.repeat(64)

/** Who is allowed to speak, and what it means when they do. */
export const ACTOR_META: Record<Actor, { short: string; label: string; role: string }> = {
  orchestrator: { short: 'OR', label: 'Orchestrator', role: 'Drives the batch; records terminal verdicts' },
  intake: { short: 'IN', label: 'Intake', role: 'Validates and classifies each request' },
  compliance: { short: 'CO', label: 'Compliance', role: 'Reviews or fast-tracks; can raise a veto' },
  treasury: { short: 'TR', label: 'Treasury', role: 'Decides pay_now or hold against the reserve floor' },
  resolution: { short: 'RE', label: 'Resolution', role: 'Negotiates Compliance/Treasury conflicts' },
  auditor: { short: 'AU', label: 'Auditor', role: 'Explains the chain after the fact' },
  verasettle: { short: 'VS', label: 'Verasettle', role: 'Executes approved payouts on-chain' },
  anchor: { short: 'AN', label: 'Anchor', role: 'Commits the chain head on-chain' },
  monolith: { short: 'MO', label: 'Monolith', role: 'Single-agent baseline the society is graded against' },
  policy: { short: 'PO', label: 'Policy', role: 'The written rules in force' },
}

/** The three states the chain is allowed to be in. Never asserted — computed.
 *  A pre-hash run must not be able to masquerade as a verified one. */
export function chainState(v: ChainVerification | undefined): 'verified' | 'unverified' | 'broken' {
  if (!v || !v.hashed) return 'unverified'
  return v.verified ? 'verified' : 'broken'
}
