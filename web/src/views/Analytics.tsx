import { api } from '../lib/api'
import { C, MONO, SANS } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'
import { Loading, Panel, SectionLabel, Stat } from '../components/Primitives'

function pct(v: number | null) {
  return v === null ? '—' : `${(v * 100).toFixed(1)}%`
}
function num(v: number | null) {
  return v === null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: 1 })
}

export function Analytics() {
  const { data, error } = useAsync(() => api.analytics(), [])
  if (!data) return <Loading error={error} />

  const { society, monolith } = data
  const benched = society.runs > 0

  return (
    <>
      <SectionLabel>The society against the single agent</SectionLabel>

      {!benched ? (
        <Panel>
          <div style={{ padding: '20px', fontFamily: SANS, fontSize: '13px', color: C.text.muted }}>
            No benchmarked run on disk. These numbers exist only when a run was recorded with
            both the society and the monolith over the same batch — nothing is filled in from
            memory or estimated.
          </div>
        </Panel>
      ) : (
        <Panel>
          <Row head cells={['', 'society', 'monolith', '']} />
          <Row
            cells={[
              'accuracy vs written policy',
              pct(society.accuracy),
              pct(monolith.accuracy),
              verdict(society.accuracy, monolith.accuracy, true),
            ]}
          />
          <Row
            cells={[
              'tokens per run',
              num(society.tokens),
              num(monolith.tokens),
              verdict(society.tokens, monolith.tokens, false),
            ]}
          />
          <Row
            cells={[
              'seconds per run',
              num(society.seconds),
              num(monolith.seconds),
              verdict(society.seconds, monolith.seconds, false),
            ]}
          />
        </Panel>
      )}

      <p
        style={{
          fontFamily: SANS,
          fontSize: '12px',
          color: C.text.muted,
          maxWidth: '680px',
          lineHeight: 1.6,
          margin: '18px 0 34px',
        }}
      >
        Averaged over {society.runs} benchmarked {society.runs === 1 ? 'run' : 'runs'}. The
        society is not cheaper and it is not faster — five specialists cost more than one model,
        and saying otherwise would be easy to disprove. What it buys is the column below.
      </p>

      <SectionLabel>What the single agent cannot do at any price</SectionLabel>
      <Panel>
        {data.capabilities.map((c) => (
          <div
            key={c.name}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '11px 14px',
              borderBottom: `1px solid ${C.border.hairline}`,
            }}
          >
            <span style={{ fontFamily: SANS, fontSize: '13px', color: C.text.primary, flex: 1 }}>
              {c.name}
            </span>
            <Mark ok={c.society} width={110} />
            <Mark ok={c.monolith} width={110} />
          </div>
        ))}
      </Panel>

      <div style={{ height: '34px' }} />
      <SectionLabel>Settlement and coverage</SectionLabel>
      <div style={{ display: 'flex', gap: '36px', flexWrap: 'wrap' }}>
        <Stat value={data.settlement.count} label="settlements" />
        <Stat value={data.settlement.usdc_moved} label="usdc moved" />
        <Stat value={data.settlement.chains.join(', ') || '—'} label="chains" />
        <Stat value={data.coverage.payouts} label="payouts covered" />
        <Stat
          value={`${data.coverage.hash_verified_pct}%`}
          label="hash-verified"
          tone={data.coverage.hash_verified_pct === 100 ? C.state.approved : C.state.vetoed}
        />
      </div>
    </>
  )
}

/** Says which side won a row, or says nobody did. Never rounds in our favour. */
function verdict(a: number | null, b: number | null, higherIsBetter: boolean) {
  if (a === null || b === null) return ''
  if (a === b) return 'tie'
  const societyWins = higherIsBetter ? a > b : a < b
  return societyWins ? 'society' : 'monolith'
}

function Row({ cells, head = false }: { cells: string[]; head?: boolean }) {
  const win = cells[3]
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        padding: '11px 14px',
        borderBottom: `1px solid ${C.border.hairline}`,
      }}
    >
      <span
        style={{
          fontFamily: head ? MONO : SANS,
          fontSize: head ? '10px' : '13px',
          color: head ? C.text.ghost : C.text.primary,
          letterSpacing: head ? '0.12em' : undefined,
          textTransform: head ? 'uppercase' : undefined,
          flex: 1,
        }}
      >
        {cells[0]}
      </span>
      {[1, 2].map((i) => (
        <span
          key={i}
          style={{
            fontFamily: MONO,
            fontSize: head ? '10px' : '13px',
            color: head
              ? C.text.ghost
              : (i === 1 && win === 'society') || (i === 2 && win === 'monolith')
                ? C.text.primary
                : C.text.muted,
            letterSpacing: head ? '0.12em' : undefined,
            textTransform: head ? 'uppercase' : undefined,
            width: '110px',
            textAlign: 'right',
          }}
        >
          {cells[i]}
        </span>
      ))}
      <span
        style={{
          fontFamily: MONO,
          fontSize: '9px',
          color: win === 'society' ? C.state.approved : win === 'monolith' ? C.state.vetoed : C.text.ghost,
          width: '80px',
          textAlign: 'right',
          letterSpacing: '0.06em',
        }}
      >
        {head ? '' : win}
      </span>
    </div>
  )
}

function Mark({ ok, width }: { ok: boolean; width: number }) {
  return (
    <span
      style={{
        fontFamily: MONO,
        fontSize: '11px',
        color: ok ? C.state.approved : C.text.muted,
        width,
        textAlign: 'right',
      }}
    >
      {ok ? 'yes' : 'no'}
    </span>
  )
}
