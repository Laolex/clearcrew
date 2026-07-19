import { Loading, Panel, SectionLabel } from '../components/Primitives'
import { api } from '../lib/api'
import { C, MONO, SANS } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'

/** A reviewer-facing map from Qwen configuration to the controls that constrain it. */
const RECONCILIATION_RUN = 'events-20260711-173828-n36.jsonl'
const RECONCILIATION_PAYOUT = '62c33a4f'

export function Society({ onOpenReplay }: { onOpenReplay: (run: string, subject: string) => void }) {
  const { data, error } = useAsync(() => api.society(), [])
  if (!data) return <Loading error={error} />

  return (
    <>
      <SectionLabel>Configured runtime</SectionLabel>
      <Panel>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, .7fr) 1.3fr', gap: '0', padding: '0' }}>
          <Fact label="Provider" value={data.provider} />
          <Fact label="API endpoint" value={data.endpoint} mono />
        </div>
        <div style={{ borderTop: `1px solid ${C.border.hairline}`, padding: '16px 18px' }}>
          <p style={kicker}>Models configured for this society</p>
          <div style={{ display: 'grid', gap: '10px' }}>
            {data.models.map((model) => (
              <div key={model.name} style={modelRow}>
                <code style={modelName}>{model.name}</code>
                <span style={modelPurpose}>{model.purpose}</span>
              </div>
            ))}
          </div>
        </div>
      </Panel>

      <div style={{ height: '34px' }} />
      <SectionLabel>Five agents, separated authority</SectionLabel>
      <Panel>
        {data.roles.map((role, index) => (
          <div key={role.name} style={{ ...roleRow, borderBottom: index === data.roles.length - 1 ? 'none' : `1px solid ${C.border.hairline}` }}>
            <span style={roleNumber}>{String(index + 1).padStart(2, '0')}</span>
            <strong style={roleName}>{role.name}</strong>
            <span style={roleAuthority}>{role.authority}</span>
          </div>
        ))}
      </Panel>

      <div style={{ height: '34px' }} />
      <SectionLabel>What constrains the agents</SectionLabel>
      <Panel>
        {data.controls.map((control, index) => (
          <div key={control} style={{ ...controlRow, borderBottom: index === data.controls.length - 1 ? 'none' : `1px solid ${C.border.hairline}` }}>
            <span aria-hidden="true" style={controlMark}>✓</span>
            <span>{control}</span>
          </div>
        ))}
      </Panel>
      <p style={note}>
        This page reads the live service configuration and code-level role contracts. Inspect a recorded
        run in <b>Run trail</b> to see the resulting events; inspect <b>Benchmark</b> for the controlled
        comparison with one agent.
      </p>
      <button onClick={() => onOpenReplay(RECONCILIATION_RUN, RECONCILIATION_PAYOUT)} style={replayButton}>
        Open the recorded reconciliation dispute <span>62c33a4f →</span>
      </button>
      <p style={replayNote}>
        A Treasury action contradicted its own P3 reason. The orchestrator flagged it and Resolution
        enforced the ledger — the clearest recorded example of the society checking itself.
      </p>
    </>
  )
}

function Fact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ padding: '18px', borderRight: mono ? 'none' : `1px solid ${C.border.hairline}` }}>
      <p style={kicker}>{label}</p>
      <p style={{ margin: '7px 0 0', color: C.text.primary, fontFamily: mono ? MONO : SANS, fontSize: mono ? '11px' : '14px', lineHeight: 1.5, overflowWrap: 'anywhere' }}>{value}</p>
    </div>
  )
}

const kicker = { margin: 0, color: C.text.ghost, fontFamily: MONO, fontSize: '10px', letterSpacing: '.12em', textTransform: 'uppercase' as const }
const modelRow = { display: 'grid', gridTemplateColumns: 'minmax(160px, .6fr) 1.4fr', alignItems: 'center', gap: '16px', padding: '10px 12px', background: C.bg.elevated, borderRadius: '4px' }
const modelName = { color: C.text.primary, fontFamily: MONO, fontSize: '12px' }
const modelPurpose = { color: C.text.secondary, fontFamily: SANS, fontSize: '13px', lineHeight: 1.45 }
const roleRow = { display: 'grid', gridTemplateColumns: '42px minmax(120px, .55fr) 1.45fr', alignItems: 'start', gap: '14px', padding: '14px 18px' }
const roleNumber = { color: C.text.ghost, fontFamily: MONO, fontSize: '10px', paddingTop: '3px' }
const roleName = { color: C.text.primary, fontFamily: SANS, fontSize: '13px' }
const roleAuthority = { color: C.text.secondary, fontFamily: SANS, fontSize: '13px', lineHeight: 1.45 }
const controlRow = { display: 'flex', gap: '10px', alignItems: 'flex-start', padding: '13px 18px', color: C.text.secondary, fontFamily: SANS, fontSize: '13px', lineHeight: 1.5 }
const controlMark = { color: C.state.approved, fontFamily: MONO, fontSize: '12px', paddingTop: '1px' }
const note = { maxWidth: '760px', margin: '16px 0 0', color: C.text.muted, fontFamily: SANS, fontSize: '12px', lineHeight: 1.6 }
const replayButton = { marginTop: '22px', fontFamily: MONO, fontSize: '11px', background: C.bg.elevated, color: C.text.primary, border: `1px solid ${C.border.strong}`, borderRadius: '3px', padding: '9px 13px', cursor: 'pointer' }
const replayNote = { maxWidth: '680px', margin: '9px 0 0', color: C.text.muted, fontFamily: SANS, fontSize: '12px', lineHeight: 1.55 }
