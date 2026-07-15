import { useState } from 'react'
import { api } from '../lib/api'
import { C, MONO, SANS } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'
import { Loading, Panel, SectionLabel } from '../components/Primitives'

// A veto is the system working. A benchmark miss is the system being wrong.
// Presenting them in one undifferentiated list would flatter the society.
const KIND: Record<string, { tone: string; note: string }> = {
  compliance_vetoes: {
    tone: C.state.vetoed,
    note: 'Compliance refused a payout. This is the system working as designed.',
  },
  treasury_rejects: {
    tone: C.state.held,
    note: 'Treasury declined to fund. Also the system working — money it did not have.',
  },
  disputes_resolved: {
    tone: C.state.hypothetical,
    note: 'A veto went to Resolution and was ruled on.',
  },
  benchmark_misses: {
    tone: C.state.rejected,
    note: 'The society reached a verdict the written policy disagrees with. These are the ones that matter — the society was wrong.',
  },
  settlement_failures: {
    tone: C.state.rejected,
    note: 'An approved payout failed to settle on-chain.',
  },
}

export function Failures({ onOpen }: { onOpen: (run: string, subject: string) => void }) {
  const { data, error } = useAsync(() => api.failures(), [])
  const [open, setOpen] = useState<string>('benchmark_misses')
  if (!data) return <Loading error={error} />

  const active = data.categories.find((c) => c.key === open) ?? data.categories[0]
  const kind = KIND[active.key] ?? { tone: C.text.secondary, note: '' }

  return (
    <>
      <SectionLabel>Where it went wrong — and where it went right by refusing</SectionLabel>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '18px' }}>
        {data.categories.map((c) => {
          const on = c.key === active.key
          const tone = KIND[c.key]?.tone ?? C.text.secondary
          return (
            <button
              key={c.key}
              onClick={() => setOpen(c.key)}
              style={{
                fontFamily: MONO,
                fontSize: '11px',
                background: on ? C.bg.elevated : 'transparent',
                color: on ? C.text.primary : C.text.muted,
                border: `1px solid ${on ? tone : C.border.hairline}`,
                borderRadius: '3px',
                padding: '6px 10px',
                cursor: 'pointer',
              }}
            >
              {c.label} · <span style={{ color: c.count ? tone : C.text.ghost }}>{c.count}</span>
            </button>
          )
        })}
      </div>

      <p
        style={{
          fontFamily: SANS,
          fontSize: '12px',
          color: C.text.muted,
          maxWidth: '660px',
          lineHeight: 1.6,
          margin: '0 0 18px',
        }}
      >
        {kind.note}
      </p>

      <Panel>
        {active.items.length === 0 && (
          <div style={{ padding: '20px', fontFamily: SANS, fontSize: '13px', color: C.text.muted }}>
            {active.key === 'benchmark_misses'
              ? 'The society never disagreed with the written policy on a recorded run.'
              : active.key === 'settlement_failures'
                ? 'No approved payout has ever failed to settle.'
                : 'Nothing recorded in this category.'}
          </div>
        )}
        {active.items.map((it) => (
          <div
            key={`${it.run}:${it.id}`}
            style={{
              display: 'flex',
              gap: '16px',
              padding: '10px 14px',
              borderBottom: `1px solid ${C.border.hairline}`,
              alignItems: 'flex-start',
            }}
          >
            <button
              onClick={() => onOpen(it.run, it.id)}
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
                flexShrink: 0,
              }}
            >
              {it.id}
            </button>
            <span
              style={{
                fontFamily: MONO,
                fontSize: '11px',
                color: C.text.secondary,
                width: '90px',
                textAlign: 'right',
                flexShrink: 0,
              }}
            >
              {it.amount ? `$${it.amount.toLocaleString()}` : '—'}
            </span>
            {/* The agent's own words. Never paraphrased. */}
            <span
              style={{
                fontFamily: SANS,
                fontSize: '13px',
                color: C.text.primary,
                lineHeight: 1.55,
                flex: 1,
              }}
            >
              {it.reason ?? '— no reason recorded —'}
            </span>
          </div>
        ))}
      </Panel>

      {data.by_rule.length > 0 && (
        <>
          <div style={{ height: '32px' }} />
          <SectionLabel>Vetoes by the rule they cited</SectionLabel>
          <div style={{ display: 'flex', gap: '28px' }}>
            {data.by_rule.map((r) => (
              <div key={r.rule}>
                <div style={{ fontFamily: MONO, fontSize: '16px', color: C.state.vetoed }}>
                  {r.count}
                </div>
                <div style={{ fontFamily: MONO, fontSize: '10px', color: C.text.ghost, marginTop: '2px' }}>
                  {r.rule}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}
