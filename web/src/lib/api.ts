import type { ChainVerification, ClearEvent, Explain, RunDetail, RunSummary } from './domain'

// The API token is optional server-side (require_auth is a no-op when unset),
// so we only send the header when one was actually configured at build time.
const TOKEN = import.meta.env.VITE_API_TOKEN as string | undefined

/**
 * Kept in one place so every browser request has identical auth behaviour.
 *
 * A Vite environment variable is bundled into client code, so this is a
 * convenience credential for a private demo—not a substitute for server-side
 * session authentication.
 */
export function authHeaders(): HeadersInit {
  return TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`)
  return res.json() as Promise<T>
}


export interface RunEvents {
  run: string
  t0: number
  chain: ChainVerification
  untrusted_from: number | null
  events: ClearEvent[]
}

export interface Overview {
  totals: {
    runs: number
    payouts: number
    settlements: number
    usdc_moved: number
    replay_pct: number
    hash_verified_pct: number
  }
  recent: {
    run: string
    id: string
    amount: number | null
    status: string
    settled: boolean
    disputed: boolean
    miss: boolean
  }[]
}

export interface FailureItem {
  run: string
  id: string
  amount: number | null
  reason: string | null
}

export interface Failures {
  categories: { key: string; label: string; count: number; items: FailureItem[] }[]
  by_rule: { rule: string; count: number }[]
}

export interface Analytics {
  society: { accuracy: number | null; tokens: number | null; seconds: number | null; runs: number }
  monolith: { accuracy: number | null; tokens: number | null; seconds: number | null; runs: number }
  capabilities: { name: string; society: boolean; monolith: boolean }[]
  settlement: { count: number; usdc_moved: number; chains: string[] }
  coverage: { payouts: number; replay_pct: number; hash_verified_pct: number }
}

export interface Policies {
  current: string
  versions: {
    version: string
    enacted: string
    reason: string
    params: Record<string, unknown>
    rendered: string
  }[]
  note: string
}

export interface Counterfactual {
  run: string
  note: string
  policy_in_force: Record<string, unknown>
  policy_hypothetical: Record<string, unknown>
  summary: {
    in_force: { approve: number; reject: number }
    hypothetical: { approve: number; reject: number }
  }
  changes: {
    payout_id: string
    amount: number
    recorded_outcome: string | null
    in_force: { verdict: string; rule: string | null }
    hypothetical: { verdict: string; rule: string | null }
    cause: string
  }[]
}

export interface AnchorEvidence {
  run: string
  anchors: {
    event_id: string
    head_hash: string | null
    provider: string | null
    url: string | null
    tsa_time: string | null
    serial: number | null
    verification: { valid: boolean; reason?: string; gen_time?: string | null }
  }[]
}

export const api = {
  runs: () => get<{ runs: RunSummary[] }>('/api/runs'),
  run: (name: string) => get<RunDetail>(`/api/runs/${name}`),
  events: (name: string) => get<RunEvents>(`/api/runs/${name}/events`),
  anchors: (name: string) => get<AnchorEvidence>(`/api/runs/${name}/anchors`),
  explain: (run: string, subject: string) => get<Explain>(`/api/runs/${run}/explain/${subject}`),
  counterfactual: (run: string, params: Record<string, number | undefined>) => {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && Number.isFinite(v)) q.set(k, String(v))
    }
    return get<Counterfactual>(`/api/runs/${run}/counterfactual?${q}`)
  },
  overview: () => get<Overview>('/api/overview'),
  failures: () => get<Failures>('/api/failures'),
  analytics: () => get<Analytics>('/api/analytics'),
  policies: () => get<Policies>('/api/policies'),
}
