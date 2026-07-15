// In-browser simulation of the judge workspace. No network, no funds.
// Ports the retired /api/demo/* logic with a real SHA-256 hash chain.

const GENESIS = '0'.repeat(64)
const NOTICE = 'Simulated — runs entirely in your browser. No funds move and no recorded run changes.'

export interface SimEvent {
  id: string; ts: number; type: string; subject: string; actor: string
  payload: Record<string, unknown>; prev_hash: string; event_hash: string
}
export interface SimPayout {
  id: string; recipient: string; corridor: string; amount: number; memo: string
  risk: 'low' | 'medium' | 'high'; status: 'pending' | 'held' | 'settled'
}
export interface SimSession {
  id: string; created_at: number; notice: string
  chain: { hashed: boolean; verified: boolean; events: number }
  events: SimEvent[]; payouts: SimPayout[]
}

interface Internal { id: string; created_at: number; events: SimEvent[]; payouts: Map<string, SimPayout> }
const sessions = new Map<string, Internal>()

const hex = () => crypto.randomUUID().replace(/-/g, '')

function canonical(v: unknown): string {
  if (v === null || typeof v !== 'object') return JSON.stringify(v)
  if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']'
  const o = v as Record<string, unknown>
  return '{' + Object.keys(o).sort().map((k) => JSON.stringify(k) + ':' + canonical(o[k])).join(',') + '}'
}

async function eventHash(e: SimEvent): Promise<string> {
  const material = { id: e.id, ts: e.ts, type: e.type, subject: e.subject, actor: e.actor, payload: e.payload, prev_hash: e.prev_hash }
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical(material)))
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

async function append(s: Internal, type: string, subject: string, actor: string, payload: Record<string, unknown>): Promise<void> {
  const e: SimEvent = {
    id: hex().slice(0, 12), ts: Date.now() / 1000, type, subject, actor,
    payload: { ...payload, demo: true },
    prev_hash: s.events.length ? s.events[s.events.length - 1].event_hash : GENESIS,
    event_hash: '',
  }
  e.event_hash = await eventHash(e)
  s.events.push(e)
}

async function verifyChain(events: SimEvent[]): Promise<{ hashed: boolean; verified: boolean; events: number }> {
  if (!events.length) return { hashed: false, verified: false, events: 0 }
  let prev = GENESIS
  for (const e of events) {
    if (e.prev_hash !== prev || (await eventHash(e)) !== e.event_hash) return { hashed: true, verified: false, events: events.length }
    prev = e.event_hash
  }
  return { hashed: true, verified: true, events: events.length }
}

async function snapshot(s: Internal): Promise<SimSession> {
  return {
    id: s.id, created_at: s.created_at, notice: NOTICE,
    chain: await verifyChain(s.events),
    events: s.events.map((e) => ({ ...e })),
    payouts: [...s.payouts.values()].map((p) => ({ ...p })),
  }
}

function require_(id: string): Internal {
  const s = sessions.get(id)
  if (!s) throw new Error('workspace expired or does not exist')
  return s
}

export const simDemo = {
  async create(): Promise<SimSession> {
    const s: Internal = { id: hex(), created_at: Date.now() / 1000, events: [], payouts: new Map() }
    await append(s, 'batch.received', 'demo-batch', 'orchestrator', { count: 0, source: 'judge workspace — simulated, no funds move' })
    sessions.set(s.id, s)
    return snapshot(s)
  },
  async payout(id: string, input: { recipient: string; corridor: string; amount: number; memo: string }): Promise<SimSession> {
    const s = require_(id)
    const pid = `judge-${hex().slice(0, 6)}`
    const risk = input.amount >= 10_000 ? 'high' : input.amount >= 3_000 ? 'medium' : 'low'
    s.payouts.set(pid, { id: pid, ...input, risk, status: 'pending' })
    await append(s, 'intake.classified', pid, 'intake', { risk_tier: risk, reason: 'submitted in judge workspace', flags: [] })
    await append(s, 'payout.proposed', pid, 'orchestrator', { verdict: 'approve', reason: 'awaiting judge action' })
    return snapshot(s)
  },
  async decide(id: string, payoutId: string, action: 'settle' | 'hold'): Promise<SimSession> {
    const s = require_(id)
    const p = s.payouts.get(payoutId)
    if (!p) throw new Error('no such demo payout')
    if (p.status !== 'pending') throw new Error('this demo payout already has a recorded decision')
    if (action === 'hold') {
      await append(s, 'compliance.reviewed', payoutId, 'compliance', { verdict: 'veto', reason: 'held by judge for review', policy_rule: 'P2' })
      await append(s, 'treasury.decided', payoutId, 'treasury', { payout_id: payoutId, action: 'reject', reason: 'judge chose hold' })
      await append(s, 'payout.rejected', payoutId, 'orchestrator', { reason: 'held in judge workspace' })
      p.status = 'held'
    } else {
      await append(s, 'compliance.reviewed', payoutId, 'compliance', { verdict: 'clear', reason: 'cleared in judge workspace', policy_rule: 'none' })
      await append(s, 'treasury.decided', payoutId, 'treasury', { payout_id: payoutId, action: 'pay_now', reason: 'judge chose settle' })
      await append(s, 'payout.approved', payoutId, 'orchestrator', { reason: 'judge approved simulated payout' })
      await append(s, 'settlement.requested', payoutId, 'verasettle', { rail: 'simulated' })
      await append(s, 'settlement.confirmed', payoutId, 'verasettle', { rail: 'simulated', source_amount_usd: p.amount, settled_amount_usdc: p.amount, chain: 'demo-only', tx_hash: null })
      await append(s, 'payout.settled', payoutId, 'orchestrator', { reason: 'simulated settlement complete' })
      p.status = 'settled'
    }
    return snapshot(s)
  },
}
