import { useState } from 'react'
import { api, type Counterfactual as CF } from '../lib/api'
import { C, MONO, SANS } from '../lib/tokens'
import { Loading, Panel, SectionLabel } from '../components/Primitives'

/** Re-fold a recorded batch through a policy that was never enacted.
 *
 *  Everything on this page is hypothetical, and it has to stay obviously
 *  hypothetical even when it is screenshotted out of context and shown to
 *  someone who never saw this sentence — hence the standing banner and the
 *  dashed, tinted treatment on every hypothetical figure. No model is called:
 *  only the deterministic P1/P2/P3 layer is re-evaluated, and the recorded
 *  agent judgments are replayed exactly as they were written. */
export function Counterfactual({ run }: { run: string | null }) {
  const [floor, setFloor] = useState('')
  const [amount, setAmount] = useState('')
  const [age, setAge] = useState('')
  const [data, setData] = useState<CF | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!run) return <Loading error="Select a run first." />

  const numOrUndef = (s: string) => (s.trim() === '' ? undefined : Number(s))

  async function fold() {
    if (!run) return
    setBusy(true)
    setError(null)
    try {
      setData(
        await api.counterfactual(run, {
          reserve_floor: numOrUndef(floor),
          p2_amount: numOrUndef(amount),
          p2_age_days: numOrUndef(age),
        }),
      )
    } catch (e) {
      setError((e as Error).message)
      setData(null)
    } finally {
      setBusy(false)
    }
  }

  const touched = floor || amount || age

  return (
    <>
      <SectionLabel>What a different rule would have decided</SectionLabel>

      <div
        style={{
          background: '#1A1424',
          border: `1px dashed ${C.state.hypothetical}`,
          borderRadius: '4px',
          padding: '12px 14px',
          marginBottom: '22px',
          maxWidth: '760px',
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontSize: '10px',
            color: C.state.hypothetical,
            letterSpacing: '0.12em',
            marginBottom: '5px',
          }}
        >
          HYPOTHETICAL · NEVER ENACTED · NOT A RECORDED OUTCOME
        </div>
        <div style={{ fontFamily: SANS, fontSize: '12px', color: C.text.secondary, lineHeight: 1.6 }}>
          This re-folds the same recorded batch through a policy that does not exist. Only the
          deterministic layer is re-evaluated — no agent is re-run and no judgment is
          re-generated. Nothing on this page happened.
        </div>
      </div>

      <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-end', marginBottom: '26px', flexWrap: 'wrap' }}>
        <Field label="reserve floor" placeholder="10000" value={floor} onChange={setFloor} />
        <Field label="P2 amount" placeholder="9000" value={amount} onChange={setAmount} />
        <Field label="P2 age (days)" placeholder="7" value={age} onChange={setAge} />
        <button
          onClick={fold}
          disabled={busy || !touched}
          style={{
            fontFamily: MONO,
            fontSize: '11px',
            background: touched ? C.bg.elevated : 'transparent',
            color: touched ? C.text.primary : C.text.ghost,
            border: `1px solid ${touched ? C.state.hypothetical : C.border.hairline}`,
            borderRadius: '3px',
            padding: '8px 14px',
            cursor: touched ? 'pointer' : 'not-allowed',
          }}
        >
          {busy ? 'folding…' : 're-fold this batch'}
        </button>
      </div>

      {error && (
        <div style={{ fontFamily: MONO, fontSize: '12px', color: C.state.rejected, marginBottom: '18px' }}>
          {error}
        </div>
      )}

      {data && (
        <>
          <div style={{ display: 'flex', gap: '40px', marginBottom: '26px' }}>
            <Tally label="as recorded" v={data.summary.in_force} tone={C.text.primary} />
            <Tally label="hypothetical" v={data.summary.hypothetical} tone={C.state.hypothetical} dashed />
          </div>

          <SectionLabel>
            {data.changes.length === 0
              ? 'Nothing would have changed'
              : `${data.changes.length} ${data.changes.length === 1 ? 'payout' : 'payouts'} would have flipped`}
          </SectionLabel>

          <Panel>
            {data.changes.length === 0 && (
              <div style={{ padding: '20px', fontFamily: SANS, fontSize: '13px', color: C.text.muted }}>
                Under this policy every payout lands exactly where it landed in the recording.
                A parameter you can move without changing an outcome is a parameter that was
                never binding on this batch.
              </div>
            )}
            {data.changes.map((c) => (
              <div
                key={c.payout_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px',
                  padding: '11px 14px',
                  borderBottom: `1px solid ${C.border.hairline}`,
                }}
              >
                <span style={{ fontFamily: MONO, fontSize: '11px', color: C.text.secondary, width: '76px' }}>
                  {c.payout_id}
                </span>
                <span
                  style={{
                    fontFamily: MONO,
                    fontSize: '12px',
                    color: C.text.secondary,
                    width: '90px',
                    textAlign: 'right',
                  }}
                >
                  ${c.amount.toLocaleString()}
                </span>

                {/* recorded → hypothetical, and the arrow is the only claim made */}
                <span
                  style={{
                    fontFamily: MONO,
                    fontSize: '11px',
                    color: c.in_force.verdict === 'approve' ? C.state.approved : C.state.rejected,
                    width: '80px',
                  }}
                >
                  {c.in_force.verdict}
                </span>
                <span style={{ color: C.text.ghost, fontSize: '11px' }}>→</span>
                <span
                  style={{
                    fontFamily: MONO,
                    fontSize: '11px',
                    color: C.state.hypothetical,
                    border: `1px dashed ${C.state.hypothetical}66`,
                    borderRadius: '3px',
                    padding: '2px 7px',
                    width: '86px',
                    textAlign: 'center',
                  }}
                >
                  {c.hypothetical.verdict}
                </span>

                <span style={{ fontFamily: SANS, fontSize: '12px', color: C.text.muted, flex: 1 }}>
                  {c.cause}
                </span>

                {c.recorded_outcome && (
                  <span style={{ fontFamily: MONO, fontSize: '10px', color: C.text.ghost }}>
                    recorded: {c.recorded_outcome}
                  </span>
                )}
              </div>
            ))}
          </Panel>

          <p
            style={{
              fontFamily: SANS,
              fontSize: '11px',
              color: C.text.ghost,
              marginTop: '14px',
              maxWidth: '700px',
              lineHeight: 1.6,
            }}
          >
            {data.note}
          </p>
        </>
      )}
    </>
  )
}

function Field({
  label,
  placeholder,
  value,
  onChange,
}: {
  label: string
  placeholder: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <label style={{ display: 'block' }}>
      <div
        style={{
          fontFamily: MONO,
          fontSize: '9px',
          color: C.text.ghost,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          marginBottom: '5px',
        }}
      >
        {label}
      </div>
      <input
        type="number"
        min={0}
        value={value}
        placeholder={`in force: ${placeholder}`}
        onChange={(e) => onChange(e.target.value)}
        style={{
          fontFamily: MONO,
          fontSize: '12px',
          background: C.bg.surface,
          color: C.text.primary,
          border: `1px solid ${C.border.hairline}`,
          borderRadius: '3px',
          padding: '7px 9px',
          width: '150px',
          outline: 'none',
        }}
      />
    </label>
  )
}

function Tally({
  label,
  v,
  tone,
  dashed = false,
}: {
  label: string
  v: { approve: number; reject: number }
  tone: string
  dashed?: boolean
}) {
  return (
    <div
      style={{
        border: dashed ? `1px dashed ${tone}66` : `1px solid ${C.border.hairline}`,
        borderRadius: '4px',
        padding: '10px 16px',
      }}
    >
      <div style={{ fontFamily: MONO, fontSize: '9px', color: C.text.ghost, letterSpacing: '0.12em' }}>
        {label.toUpperCase()}
      </div>
      <div style={{ display: 'flex', gap: '18px', marginTop: '6px' }}>
        <span style={{ fontFamily: MONO, fontSize: '15px', color: tone }}>{v.approve} approve</span>
        <span style={{ fontFamily: MONO, fontSize: '15px', color: tone }}>{v.reject} reject</span>
      </div>
    </div>
  )
}
