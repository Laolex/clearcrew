import type { ChainVerification, ClearEvent, Explain, RunDetail, RunSummary } from './domain'

// The API token is optional server-side (require_auth is a no-op when unset),
// so we only send the header when one was actually configured at build time.
const TOKEN = import.meta.env.VITE_API_TOKEN as string | undefined

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {},
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

export const api = {
  runs: () => get<{ runs: RunSummary[] }>('/api/runs'),
  run: (name: string) => get<RunDetail>(`/api/runs/${name}`),
  events: (name: string) => get<RunEvents>(`/api/runs/${name}/events`),
  explain: (run: string, subject: string) => get<Explain>(`/api/runs/${run}/explain/${subject}`),
  counterfactual: (run: string, params: Record<string, number | undefined>) => {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) q.set(k, String(v))
    }
    return get<unknown>(`/api/runs/${run}/counterfactual?${q}`)
  },
  overview: () => get<unknown>('/api/overview'),
  failures: () => get<unknown>('/api/failures'),
  analytics: () => get<unknown>('/api/analytics'),
  policies: () => get<unknown>('/api/policies'),
}
