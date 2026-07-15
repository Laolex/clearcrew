import { api } from '../lib/api'
import { C, MONO, SANS } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'
import { Loading, Panel, SectionLabel, Stat } from '../components/Primitives'

const STATUS_COLOR: Record<string, string> = {
  approved: C.state.approved,
  settled: C.state.approved,
  rejected: C.state.rejected,
  pending: C.text.muted,
}

export function Overview({ onOpen }: { onOpen: (run: string, subject: string) => void }) {
  const { data, error } = useAsync(() => api.overview(), [])
  if (!data) return <Loading error={error} />

  const t = data.totals

  return (
    <>
      <SectionLabel>Everything recorded, across every run</SectionLabel>
      <div style={{ display: 'flex', gap: '36px', marginBottom: '14px', flexWrap: 'wrap' }}>
        <Stat value={t.runs} label="runs" />
        <Stat value={t.payouts} label="payouts" />
        <Stat value={t.settlements} label="settled on-chain" />
        <Stat value={t.usdc_moved} label="usdc moved" />
        <Stat
          value={`${t.hash_verified_pct}%`}
          label="hash-verified"
          tone={t.hash_verified_pct === 100 ? C.state.approved : C.state.vetoed}
        />
        <Stat value={`${t.replay_pct}%`} label="replayable" />
      </div>
      <p
        style={{
          fontFamily: SANS,
          fontSize: '12px',
          color: C.text.muted,
          maxWidth: '660px',
          lineHeight: 1.6,
          margin: '0 0 32px',
        }}
      >
        Every figure here is counted off the recorded logs — the runs on disk, the events in
        them, and the settlement receipts they produced. Nothing is estimated, and there is
        no figure on this page that is not derived from a file you can read.
      </p>

      <SectionLabel>Most recent payouts</SectionLabel>
      <Panel>
        {data.recent.map((p) => (
          <div
            key={`${p.run}:${p.id}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '9px 14px',
              borderBottom: `1px solid ${C.border.hairline}`,
            }}
          >
            <button
              onClick={() => onOpen(p.run, p.id)}
              style={{
                fontFamily: MONO,
                fontSize: '11px',
                color: C.text.secondary,
                background: 'transparent',
                border: 'none',
                borderBottom: `1px dotted ${C.border.strong}`,
                padding: 0,
                cursor: 'pointer',
                width: '76px',
                textAlign: 'left',
              }}
            >
              {p.id}
            </button>
            <span
              style={{
                fontFamily: MONO,
                fontSize: '12px',
                color: STATUS_COLOR[p.status] ?? C.text.secondary,
                width: '90px',
              }}
            >
              {p.status}
            </span>
            <span
              style={{
                fontFamily: MONO,
                fontSize: '12px',
                color: C.text.secondary,
                width: '100px',
                textAlign: 'right',
              }}
            >
              {p.amount ? `$${p.amount.toLocaleString()}` : '—'}
            </span>
            {p.disputed && <Tag color={C.state.hypothetical}>disputed</Tag>}
            {p.settled && <Tag color={C.state.approved}>on-chain</Tag>}
            {/* A miss is the society getting it wrong. It is shown, not buried. */}
            {p.miss && <Tag color={C.state.rejected}>disagreed with policy</Tag>}
            <span style={{ flex: 1 }} />
            <span style={{ fontFamily: MONO, fontSize: '10px', color: C.text.ghost }}>
              {p.run.replace('events-', '').replace('.jsonl', '')}
            </span>
          </div>
        ))}
      </Panel>
    </>
  )
}

function Tag({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span
      style={{
        fontFamily: MONO,
        fontSize: '9px',
        color,
        border: `1px solid ${color}44`,
        background: `${color}14`,
        borderRadius: '3px',
        padding: '2px 6px',
        letterSpacing: '0.06em',
      }}
    >
      {children}
    </span>
  )
}
