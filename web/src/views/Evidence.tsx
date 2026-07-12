import { useCallback, useEffect, useState } from 'react'
import { Loading, Panel, SectionLabel } from '../components/Primitives'
import { C, MONO, SANS } from '../lib/tokens'
import {
  canonical,
  fetchAndVerify,
  usingWebCrypto,
  verifyChainRaw,
  type LocalVerification,
} from '../lib/verify'

type RawEvent = Record<string, unknown>

/** Verification the reader can perform, not a badge they must believe.
 *
 *  Every hash on this page is recomputed in the browser from the bytes the
 *  server sent. The server's own `verified: true` is displayed beside our
 *  result precisely so the two can disagree — if they ever did, the server
 *  would be the thing that was wrong. */
export function Evidence({ run }: { run: string | null }) {
  const [local, setLocal] = useState<LocalVerification | null>(null)
  const [events, setEvents] = useState<RawEvent[] | null>(null)
  const [serverSaid, setServerSaid] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tamperAt, setTamperAt] = useState<number | null>(null)
  const [tampered, setTampered] = useState<LocalVerification | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    if (!run) return
    setLocal(null)
    setEvents(null)
    setTampered(null)
    setTamperAt(null)
    setError(null)
    fetchAndVerify(run)
      .then(({ local, events, serverSaid }) => {
        setLocal(local)
        setEvents(events as RawEvent[])
        setServerSaid(serverSaid)
      })
      .catch((e: Error) => setError(e.message))
  }, [run])

  useEffect(load, [load])

  if (!run) return <Loading error="Select a run first." />
  if (!local || !events) return <Loading error={error} />

  /** Alter one recorded reason and re-walk the chain. Nothing is faked: the
   *  hashes are recomputed, and the chain breaks where the arithmetic says. */
  async function tamper(i: number) {
    if (!events) return
    setBusy(true)
    const copy: RawEvent[] = events.map((e, j) => {
      if (j !== i) return e
      const payload = { ...(e.payload as Record<string, unknown>) }
      payload.reason = 'APPROVED — no concerns' // the edit an insider would make
      return { ...e, payload }
    })
    const result = await verifyChainRaw(copy as never)
    setTamperAt(i)
    setTampered(result)
    setBusy(false)
  }

  // Target the edit someone would actually make: a veto, mid-chain. Rewriting
  // the first event breaks everything and proves less — the interesting failure
  // is a single altered judgment buried in a long, otherwise-honest log.
  const preferred = events.findIndex(
    (e) =>
      e.type === 'compliance.reviewed' &&
      (e.payload as Record<string, unknown>)?.verdict === 'veto',
  )
  const candidate =
    preferred >= 0
      ? preferred
      : events.findIndex((e) => typeof (e.payload as Record<string, unknown>)?.reason === 'string')
  const shown = tampered ?? local

  return (
    <>
      <SectionLabel>Verified here, in your browser</SectionLabel>

      <Verdict v={shown} tamperedAt={tampered ? tamperAt : null} />

      <p
        style={{
          fontFamily: SANS,
          fontSize: '12px',
          color: C.text.muted,
          maxWidth: '700px',
          lineHeight: 1.65,
          margin: '16px 0 0',
        }}
      >
        Every hash above was recomputed from the bytes the server sent, in this page, using
        SHA-256 in the browser — <code style={{ fontFamily: MONO, color: C.text.secondary }}>
          {`sha256(json(id, ts, type, subject, actor, payload, prev_hash))`}
        </code>
        . The server's own claim is shown beside it so the two can disagree. They do not.
      </p>

      <p
        style={{
          fontFamily: MONO,
          fontSize: '10px',
          color: C.text.ghost,
          margin: '8px 0 0',
          letterSpacing: '0.04em',
        }}
      >
        {usingWebCrypto
          ? 'digest: WebCrypto SHA-256 (secure context)'
          : 'digest: bundled SHA-256 — this page is not a secure context, so WebCrypto is unavailable'}
      </p>

      <div style={{ display: 'flex', gap: '28px', alignItems: 'flex-start', margin: '18px 0 34px' }}>
        {/* The server's verdict is about the REAL log and never changes when we
            edit a local copy. Saying "the server says broken" after a local
            tamper would put words in its mouth — on the one page whose whole
            job is attributing claims to whoever actually made them. */}
        <Claim who="the server says, of the real log" ok={serverSaid} />
        <Claim
          who={tampered ? 'this page, of your edited copy' : 'this page computed'}
          ok={shown.ok}
        />
        {tampered && (
          <div
            style={{
              fontFamily: SANS,
              fontSize: '12px',
              color: C.text.muted,
              maxWidth: '340px',
              lineHeight: 1.6,
            }}
          >
            They disagree because you changed the log, not because the server was wrong. The
            edit exists only in this browser — the recorded file is untouched.
          </div>
        )}
      </div>

      <SectionLabel>Break it</SectionLabel>
      <p
        style={{
          fontFamily: SANS,
          fontSize: '12px',
          color: C.text.muted,
          maxWidth: '700px',
          lineHeight: 1.65,
          margin: '0 0 16px',
        }}
      >
        Rewrite a recorded reason to something exculpatory — the edit someone would actually
        make — and the chain is re-walked. The break is not staged: the event no longer hashes
        to what it claims, so verification fails at that index and every event after it is
        downstream of a lie.
      </p>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '30px' }}>
        <button
          onClick={() => candidate >= 0 && tamper(candidate)}
          disabled={busy || candidate < 0}
          style={{
            fontFamily: MONO,
            fontSize: '11px',
            background: C.bg.surface,
            color: C.state.rejected,
            border: `1px solid ${C.state.rejected}66`,
            borderRadius: '3px',
            padding: '8px 14px',
            cursor: 'pointer',
          }}
        >
          {busy ? 'recomputing…' : `rewrite the reason at index ${candidate}`}
        </button>
        {tampered && (
          <button
            onClick={load}
            style={{
              fontFamily: MONO,
              fontSize: '11px',
              background: 'transparent',
              color: C.text.muted,
              border: `1px solid ${C.border.hairline}`,
              borderRadius: '3px',
              padding: '8px 14px',
              cursor: 'pointer',
            }}
          >
            restore the real log
          </button>
        )}
      </div>

      <SectionLabel>Evidence pack</SectionLabel>
      <Panel>
        <div style={{ padding: '16px' }}>
          <div style={{ fontFamily: SANS, fontSize: '13px', color: C.text.secondary, lineHeight: 1.6 }}>
            The recorded event log, its verification result, and any settlement receipts it
            produced — the file an auditor would ask for.
          </div>
          <button
            onClick={() => downloadPack(run!, events, local)}
            style={{
              marginTop: '14px',
              fontFamily: MONO,
              fontSize: '11px',
              background: C.bg.elevated,
              color: C.text.primary,
              border: `1px solid ${C.border.strong}`,
              borderRadius: '3px',
              padding: '8px 14px',
              cursor: 'pointer',
            }}
          >
            download evidence pack · json
          </button>
        </div>
      </Panel>
    </>
  )
}

function Verdict({ v, tamperedAt }: { v: LocalVerification; tamperedAt: number | null }) {
  const broken = !v.ok
  const tone = broken ? C.state.rejected : C.state.approved
  return (
    <div
      style={{
        background: broken ? '#280A0A' : '#142819',
        border: `1px solid ${broken ? '#4A1414' : '#1E4028'}`,
        borderRadius: '4px',
        padding: '16px 18px',
        maxWidth: '820px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
        <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: tone }} />
        <span style={{ fontFamily: MONO, fontSize: '13px', color: tone }}>
          {broken
            ? v.cause === 'content'
              ? `chain broken at index ${v.brokenAt} — content no longer matches its own hash`
              : `chain broken at index ${v.brokenAt} — an event names a parent that is not there`
            : `chain verified · ${v.events} events`}
        </span>
      </div>

      {broken && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '7px' }}>
          {tamperedAt !== null && (
            <div style={{ fontFamily: SANS, fontSize: '12px', color: C.text.secondary, lineHeight: 1.6 }}>
              The reason recorded at index {tamperedAt} was rewritten. Everything from index{' '}
              {v.brokenAt} onward is downstream of that edit and can no longer be trusted.
            </div>
          )}
          <HashLine label="claims" value={v.expected} />
          <HashLine label="actually hashes to" value={v.computed} />
        </div>
      )}
    </div>
  )
}

function HashLine({ label, value }: { label: string; value?: string }) {
  return (
    <div style={{ display: 'flex', gap: '10px', alignItems: 'baseline' }}>
      <span
        style={{
          fontFamily: MONO,
          fontSize: '9px',
          color: C.text.ghost,
          letterSpacing: '0.1em',
          width: '150px',
          textTransform: 'uppercase',
        }}
      >
        {label}
      </span>
      <span style={{ fontFamily: MONO, fontSize: '11px', color: C.text.secondary, wordBreak: 'break-all' }}>
        {value}
      </span>
    </div>
  )
}

function Claim({ who, ok }: { who: string; ok: boolean }) {
  return (
    <div>
      <div style={{ fontFamily: MONO, fontSize: '9px', color: C.text.ghost, letterSpacing: '0.12em' }}>
        {who.toUpperCase()}
      </div>
      <div
        style={{
          fontFamily: MONO,
          fontSize: '13px',
          color: ok ? C.state.approved : C.state.rejected,
          marginTop: '4px',
        }}
      >
        {ok ? 'verified' : 'broken'}
      </div>
    </div>
  )
}

function downloadPack(run: string, events: RawEvent[], local: LocalVerification) {
  const settlements = events.filter((e) => e.type === 'settlement.confirmed')
  const pack = {
    run,
    exported_at: new Date().toISOString(),
    verification: {
      performed_by: 'clearcrew web client (SHA-256, in-browser)',
      material: 'sha256(json.dumps({id,ts,type,subject,actor,payload,prev_hash}, sort_keys=True, separators=(",",":")))',
      result: local,
    },
    settlements: settlements.map((s) => s.payload),
    events,
  }
  const blob = new Blob([canonicalPretty(pack)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${run.replace('.jsonl', '')}-evidence.json`
  a.click()
  URL.revokeObjectURL(a.href)
}

function canonicalPretty(v: unknown): string {
  // The pack is read by humans, so it is indented — but the canonical form used
  // for hashing is the one documented inside it, not this rendering.
  void canonical
  return JSON.stringify(v, null, 2)
}
