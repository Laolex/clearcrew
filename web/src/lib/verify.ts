// Independent chain verification, in the browser.
//
// The server says `verified: true`. That is the server's word for it. This
// recomputes every hash from the bytes the server actually sent, so the page
// does not have to take the server's word — it would be strange for a product
// whose whole claim is "don't trust, verify" to ask the reader to trust an
// assertion of trustworthiness.
//
// The hash material must be byte-identical to events.py::_event_hash:
//
//   material = {id, ts, type, subject, actor, payload, prev_hash}
//   sha256(json.dumps(material, sort_keys=True, separators=(",", ":")))
//
// Two ways to get that wrong, both of which we hit:
//
//  1. Python's json.dumps defaults to ensure_ascii=True, escaping non-ASCII as
//     \uXXXX. JSON.stringify does not, and the recorded reasons are full of em
//     dashes.
//  2. Python distinguishes the float 9000.0 from the int 9000 and renders them
//     differently. JSON.parse collapses both to the Number 9000, destroying the
//     distinction before we can hash it. So we never parse-then-reserialize: we
//     tokenize the raw response text and keep each number's literal exactly as
//     it arrived.

type Raw = { __num: string } | string | boolean | null | Raw[] | { [k: string]: Raw }

/** JSON.parse that preserves number literals verbatim. */
export function parseRaw(text: string): Raw {
  let i = 0

  const ws = () => {
    while (i < text.length && ' \t\n\r'.includes(text[i])) i++
  }

  function value(): Raw {
    ws()
    const c = text[i]
    if (c === '{') return object()
    if (c === '[') return array()
    if (c === '"') return str()
    if (text.startsWith('true', i)) return (i += 4), true
    if (text.startsWith('false', i)) return (i += 5), false
    if (text.startsWith('null', i)) return (i += 4), null
    return number()
  }

  function object(): { [k: string]: Raw } {
    const out: { [k: string]: Raw } = {}
    i++ // {
    ws()
    if (text[i] === '}') return i++, out
    for (;;) {
      ws()
      const k = str()
      ws()
      i++ // :
      out[k] = value()
      ws()
      if (text[i] === ',') {
        i++
        continue
      }
      i++ // }
      return out
    }
  }

  function array(): Raw[] {
    const out: Raw[] = []
    i++ // [
    ws()
    if (text[i] === ']') return i++, out
    for (;;) {
      out.push(value())
      ws()
      if (text[i] === ',') {
        i++
        continue
      }
      i++ // ]
      return out
    }
  }

  function str(): string {
    const start = i
    i++ // opening quote
    while (i < text.length) {
      if (text[i] === '\\') {
        i += 2
        continue
      }
      if (text[i] === '"') {
        i++
        break
      }
      i++
    }
    return JSON.parse(text.slice(start, i)) as string
  }

  function number(): { __num: string } {
    const start = i
    while (i < text.length && /[-+0-9.eE]/.test(text[i])) i++
    return { __num: text.slice(start, i) }
  }

  return value()
}

function isNum(v: Raw): v is { __num: string } {
  return typeof v === 'object' && v !== null && !Array.isArray(v) && '__num' in v
}

function escapeNonAscii(s: string): string {
  let out = ''
  for (const ch of s) {
    const c = ch.codePointAt(0)!
    if (c > 0x7f) {
      if (c > 0xffff) {
        const v = c - 0x10000
        out += `\\u${(0xd800 + (v >> 10)).toString(16).padStart(4, '0')}`
        out += `\\u${(0xdc00 + (v & 0x3ff)).toString(16).padStart(4, '0')}`
      } else {
        out += `\\u${c.toString(16).padStart(4, '0')}`
      }
    } else {
      out += ch
    }
  }
  return out
}

/** json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) */
export function canonical(value: Raw): string {
  if (value === null) return 'null'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (isNum(value)) return value.__num
  if (typeof value === 'string') return escapeNonAscii(JSON.stringify(value))
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`
  const o = value as { [k: string]: Raw }
  const keys = Object.keys(o).sort()
  return `{${keys.map((k) => `${escapeNonAscii(JSON.stringify(k))}:${canonical(o[k])}`).join(',')}}`
}

const HASHED_KEYS = ['id', 'ts', 'type', 'subject', 'actor', 'payload', 'prev_hash'] as const

// crypto.subtle only exists in a secure context. Served over plain HTTP from
// anything but localhost — a tailnet address, an IP, a judge's local network —
// it is undefined, and a verification that silently no-ops is worse than none
// at all. So we carry our own SHA-256 and fall back to it.
const K = /* @__PURE__ */ new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
])

function sha256Sync(bytes: Uint8Array): string {
  const H = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ])
  const len = bytes.length
  const withPad = new Uint8Array((((len + 8) >> 6) + 1) * 64)
  withPad.set(bytes)
  withPad[len] = 0x80
  new DataView(withPad.buffer).setUint32(withPad.length - 4, len * 8, false)

  const w = new Uint32Array(64)
  const view = new DataView(withPad.buffer)
  const rotr = (x: number, n: number) => (x >>> n) | (x << (32 - n))

  for (let off = 0; off < withPad.length; off += 64) {
    for (let i = 0; i < 16; i++) w[i] = view.getUint32(off + i * 4, false)
    for (let i = 16; i < 64; i++) {
      const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3)
      const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10)
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0
    }
    let [a, b, c, d, e, f, g, h] = H
    for (let i = 0; i < 64; i++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
      const ch = (e & f) ^ (~e & g)
      const t1 = (h + S1 + ch + K[i] + w[i]) >>> 0
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
      const maj = (a & b) ^ (a & c) ^ (b & c)
      const t2 = (S0 + maj) >>> 0
      h = g
      g = f
      f = e
      e = (d + t1) >>> 0
      d = c
      c = b
      b = a
      a = (t1 + t2) >>> 0
    }
    H[0] = (H[0] + a) >>> 0
    H[1] = (H[1] + b) >>> 0
    H[2] = (H[2] + c) >>> 0
    H[3] = (H[3] + d) >>> 0
    H[4] = (H[4] + e) >>> 0
    H[5] = (H[5] + f) >>> 0
    H[6] = (H[6] + g) >>> 0
    H[7] = (H[7] + h) >>> 0
  }
  return [...H].map((x) => x.toString(16).padStart(8, '0')).join('')
}

/** True when the browser gave us WebCrypto; false when we hashed it ourselves.
 *  The page says which, because "who computed this" is part of the evidence. */
export const usingWebCrypto = typeof crypto !== 'undefined' && !!crypto.subtle

async function sha256(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text)
  if (usingWebCrypto) {
    const buf = await crypto.subtle.digest('SHA-256', bytes)
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('')
  }
  return sha256Sync(bytes)
}

export async function eventHash(raw: { [k: string]: Raw }): Promise<string> {
  const material: { [k: string]: Raw } = {}
  for (const k of HASHED_KEYS) material[k] = raw[k]
  return sha256(canonical(material))
}

export interface LocalVerification {
  ok: boolean
  events: number
  brokenAt: number | null
  /** These are different failures and must not read alike. */
  cause: 'content' | 'linkage' | null
  expected?: string
  computed?: string
}

const GENESIS = '0'.repeat(64)

/** Walk the chain exactly as events.py does — each event must hash to what it
 *  claims, and must name its predecessor. */
export async function verifyChainRaw(events: { [k: string]: Raw }[]): Promise<LocalVerification> {
  let prev = GENESIS
  for (let i = 0; i < events.length; i++) {
    const e = events[i]
    if (e.prev_hash !== prev) {
      return {
        ok: false,
        events: events.length,
        brokenAt: i,
        cause: 'linkage',
        expected: prev,
        computed: String(e.prev_hash),
      }
    }
    const computed = await eventHash(e)
    if (computed !== e.event_hash) {
      return {
        ok: false,
        events: events.length,
        brokenAt: i,
        cause: 'content',
        expected: String(e.event_hash),
        computed,
      }
    }
    prev = String(e.event_hash)
  }
  return { ok: true, events: events.length, brokenAt: null, cause: null }
}

/** Fetch the trail as TEXT so number literals survive, and verify it locally.
 *  `serverSaid` is the server's own verdict, kept separate from ours so the page
 *  can show the two side by side without either being put in the other's mouth. */
export async function fetchAndVerify(run: string, headers: HeadersInit = {}) {
  const res = await fetch(`/api/runs/${run}/events`, {
    headers,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  const rawText = await res.text()
  const body = parseRaw(rawText) as { [k: string]: Raw }
  const events = body.events as { [k: string]: Raw }[]
  const chain = body.chain as { [k: string]: Raw }
  return {
    local: await verifyChainRaw(events),
    events,
    serverSaid: chain?.verified === true,
    rawText,
  }
}
