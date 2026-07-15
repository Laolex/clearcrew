import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { ClearEvent, Explain } from '../lib/domain'
import { judgment, prose } from '../lib/payload'
import { C, MONO, SANS } from '../lib/tokens'
import { ActorChip, HashPill } from './Primitives'

/** The negotiated moment. Compliance vetoes, Treasury has already cleared, and
 *  Resolution rules — that opposition is the product's whole claim, so it is
 *  rendered as a confrontation rather than as three more rows in a list. */
export function DecisionDetail({
  run,
  subject,
  onClose,
}: {
  run: string
  subject: string
  onClose: () => void
}) {
  const [data, setData] = useState<Explain | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    setData(null)
    api
      .explain(run, subject)
      .then(setData)
      .catch((e: Error) => setErr(e.message))
  }, [run, subject])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const chain = data?.chain ?? []
  const veto = chain.find((e) => e.type === 'compliance.reviewed' && e.payload?.verdict === 'veto')
  const treasury = chain.find((e) => e.type === 'treasury.decided')
  const ruling = chain.find((e) => e.type === 'dispute.resolved')
  const terminal = chain.find((e) =>
    ['payout.approved', 'payout.rejected', 'payout.settled'].includes(e.type),
  )
  const audit = chain.find((e) => e.type === 'audit.explained')

  // A veto that nobody opposed is not a confrontation. Treasury often never
  // speaks on a payout compliance killed first, and staging an empty card
  // against a veto would invent a disagreement the log does not contain.
  const twoSided = Boolean(veto && treasury && ruling)
  const oneSided = Boolean(veto && ruling && !treasury)

  const payout = (data?.payout ?? {}) as Record<string, unknown>

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: '#000000CC',
        display: 'flex',
        justifyContent: 'flex-end',
        zIndex: 10,
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(760px, 92vw)',
          background: C.bg.base,
          borderLeft: `1px solid ${C.border.strong}`,
          height: '100%',
          overflowY: 'auto',
          padding: '32px 36px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '4px' }}>
          <span style={{ fontFamily: MONO, fontSize: '20px', color: C.text.primary }}>{subject}</span>
          <button
            onClick={onClose}
            style={{
              marginLeft: 'auto',
              fontFamily: MONO,
              fontSize: '11px',
              background: 'transparent',
              color: C.text.muted,
              border: `1px solid ${C.border.hairline}`,
              borderRadius: '3px',
              padding: '4px 9px',
              cursor: 'pointer',
            }}
          >
            esc
          </button>
        </div>

        {err && (
          <div style={{ fontFamily: MONO, fontSize: '12px', color: C.state.rejected }}>{err}</div>
        )}
        {!data && !err && (
          <div style={{ fontFamily: MONO, fontSize: '12px', color: C.text.muted }}>loading…</div>
        )}

        {data && (
          <>
            {/* The facts of the request, before anyone judged it. */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '22px', margin: '18px 0 28px' }}>
              {(
                [
                  ['amount', payout.amount ? `${payout.amount} ${payout.currency ?? ''}` : null],
                  [
                    'corridor',
                    payout.from_country ? `${payout.from_country}→${payout.to_country}` : null,
                  ],
                  ['account age', payout.recipient_age_days ? `${payout.recipient_age_days} days` : null],
                  ['memo', (payout.memo as string) || '— none —'],
                ] as [string, string | null][]
              ).map(([k, v]) =>
                v ? (
                  <div key={k}>
                    <div
                      style={{
                        fontFamily: MONO,
                        fontSize: '9px',
                        color: C.text.ghost,
                        letterSpacing: '0.12em',
                      }}
                    >
                      {k.toUpperCase()}
                    </div>
                    <div style={{ fontFamily: MONO, fontSize: '13px', color: C.text.secondary, marginTop: '3px' }}>
                      {v}
                    </div>
                  </div>
                ) : null,
              )}
            </div>

            {twoSided && (
              <>
                <Heading>The disagreement</Heading>
                <div style={{ display: 'flex', gap: '14px', alignItems: 'stretch' }}>
                  <Position e={treasury} side="cleared" />
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      fontFamily: MONO,
                      fontSize: '11px',
                      color: C.state.vetoed,
                      letterSpacing: '0.1em',
                    }}
                  >
                    VS
                  </div>
                  <Position e={veto} side="vetoed" />
                </div>
                <Heading>The ruling</Heading>
                <Ruling e={ruling!} />
              </>
            )}

            {oneSided && (
              <>
                <Heading>The veto</Heading>
                <p
                  style={{
                    fontFamily: SANS,
                    fontSize: '12px',
                    color: C.text.muted,
                    lineHeight: 1.6,
                    margin: '-4px 0 12px',
                    maxWidth: '620px',
                  }}
                >
                  Compliance killed this before Treasury ever weighed in, so no opposing position
                  was recorded. Resolution ruled on the veto alone — there was no negotiation.
                </p>
                <Position e={veto} side="vetoed" />
                <div style={{ height: '24px' }} />
                <Heading>The ruling</Heading>
                <Ruling e={ruling!} />
              </>
            )}

            {!twoSided && !oneSided && (
              <>
                <Heading>Uncontested</Heading>
                <p
                  style={{
                    fontFamily: SANS,
                    fontSize: '13px',
                    color: C.text.muted,
                    lineHeight: 1.6,
                    margin: '0 0 24px',
                    maxWidth: '620px',
                  }}
                >
                  No agent contested this payout — it passed through without a veto, so there was
                  nothing to negotiate. The full recorded chain is below.
                </p>
              </>
            )}

            {terminal && (
              <>
                <Heading>The verdict</Heading>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    background: C.bg.surface,
                    border: `1px solid ${C.border.hairline}`,
                    borderRadius: '4px',
                    padding: '14px 16px',
                    marginBottom: '28px',
                  }}
                >
                  <span
                    style={{
                      fontFamily: MONO,
                      fontSize: '13px',
                      color:
                        terminal.type === 'payout.rejected' ? C.state.rejected : C.state.approved,
                    }}
                  >
                    {terminal.type}
                  </span>
                  <ActorChip actor={terminal.actor} />
                  <span style={{ marginLeft: 'auto' }}>
                    <HashPill hash={terminal.event_hash} />
                  </span>
                </div>
              </>
            )}

            {audit && prose(audit) && (
              <>
                <Heading>What the auditor said afterwards</Heading>
                <div
                  style={{
                    fontFamily: SANS,
                    fontSize: '13px',
                    color: C.text.primary,
                    lineHeight: 1.65,
                    borderLeft: `2px solid ${C.border.strong}`,
                    paddingLeft: '14px',
                    marginBottom: '28px',
                  }}
                >
                  {prose(audit)}
                </div>
              </>
            )}

            <Heading>Full recorded chain · {chain.length} events</Heading>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
              {chain.map((e) => (
                <div
                  key={e.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '7px 0',
                    borderBottom: `1px solid ${C.border.hairline}`,
                  }}
                >
                  <span style={{ fontFamily: MONO, fontSize: '11px', color: C.text.muted, width: '54px' }}>
                    +{e.t_offset}s
                  </span>
                  <span style={{ fontFamily: MONO, fontSize: '11px', color: C.text.secondary, flex: 1 }}>
                    {e.type}
                  </span>
                  <ActorChip actor={e.actor} />
                  <HashPill hash={e.event_hash} />
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function Heading({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: MONO,
        fontSize: '10px',
        color: C.text.ghost,
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        margin: '0 0 12px',
      }}
    >
      {children}
    </div>
  )
}

/** One side of the argument, in the agent's own words. */
function Position({ e, side }: { e?: ClearEvent; side: 'cleared' | 'vetoed' }) {
  const accent = side === 'vetoed' ? C.state.vetoed : C.state.held
  if (!e) {
    return (
      <div
        style={{
          flex: 1,
          border: `1px dashed ${C.border.hairline}`,
          borderRadius: '4px',
          padding: '14px',
          fontFamily: SANS,
          fontSize: '12px',
          color: C.text.muted,
        }}
      >
        No position recorded on this side.
      </div>
    )
  }
  const j = judgment(e)
  return (
    <div
      style={{
        flex: 1,
        background: C.bg.surface,
        border: `1px solid ${accent}55`,
        borderTop: `2px solid ${accent}`,
        borderRadius: '4px',
        padding: '14px 16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <ActorChip actor={e.actor} />
        {j && (
          <span style={{ fontFamily: MONO, fontSize: '10px', color: accent, letterSpacing: '0.08em' }}>
            {j.label}
          </span>
        )}
      </div>
      <div style={{ fontFamily: SANS, fontSize: '13px', color: C.text.primary, lineHeight: 1.6 }}>
        {prose(e) ?? '—'}
      </div>
    </div>
  )
}

function Ruling({ e }: { e: ClearEvent }) {
  const j = judgment(e)
  const conditions = e.payload?.conditions
  return (
    <div
      style={{
        background: '#1A1424',
        border: `1px solid ${C.state.hypothetical}55`,
        borderRadius: '4px',
        padding: '16px',
        marginBottom: '28px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
        <ActorChip actor={e.actor} />
        {j && (
          <span
            style={{
              fontFamily: MONO,
              fontSize: '11px',
              color: C.state.hypothetical,
              letterSpacing: '0.08em',
            }}
          >
            {j.label}
          </span>
        )}
      </div>
      <div style={{ fontFamily: SANS, fontSize: '13px', color: C.text.primary, lineHeight: 1.65 }}>
        {prose(e) ?? '—'}
      </div>
      {conditions ? (
        <div style={{ marginTop: '10px' }}>
          <div style={{ fontFamily: MONO, fontSize: '9px', color: C.text.ghost, letterSpacing: '0.12em' }}>
            CONDITIONS
          </div>
          <div style={{ fontFamily: MONO, fontSize: '11px', color: C.text.secondary, marginTop: '3px' }}>
            {Array.isArray(conditions) ? conditions.join(', ') : String(conditions)}
          </div>
        </div>
      ) : null}
    </div>
  )
}
