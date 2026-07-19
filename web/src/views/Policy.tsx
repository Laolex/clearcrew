import { useState } from 'react'
import { api } from '../lib/api'
import type { EnactedPolicy, PolicyCompilation, PolicyImpact } from '../lib/api'
import { C, MONO, SANS } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'
import { Loading, Panel, SectionLabel } from '../components/Primitives'

export function Policy({ run }: { run: string | null }) {
  const { data, error } = useAsync(() => api.policies(), [])
  const [instruction, setInstruction] = useState('')
  const [compilation, setCompilation] = useState<PolicyCompilation | null>(null)
  const [compileError, setCompileError] = useState<string | null>(null)
  const [impact, setImpact] = useState<PolicyImpact | null>(null)
  const [enacted, setEnacted] = useState<EnactedPolicy | null>(null)
  const [submitting, setSubmitting] = useState(false)
  if (!data) return <Loading error={error} />

  async function compile() {
    if (!instruction.trim() || submitting) return
    setSubmitting(true)
    setCompileError(null)
    try {
      const result = await api.compilePolicy(instruction)
      setCompilation(result)
      setImpact(result.status === 'proposal' && run ? await api.policyImpact(result.event_id, run) : null)
      setEnacted(null)
    } catch (err) {
      setCompileError(err instanceof Error ? err.message : 'Unable to compile policy change.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <SectionLabel>The rules in force</SectionLabel>
      <Panel>
        <div style={{ padding: '16px' }}>
          <p style={{ ...kicker, marginTop: 0 }}>Propose a parameter change</p>
          <p style={{ ...copy, marginTop: 0 }}>
            Describe a change in plain English. ClearCrew can only propose changes to the existing policy parameters; it never enacts them here.
          </p>
          <textarea
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder="e.g. Reject payouts over $10,000 to accounts younger than two weeks, and add Russia to the sanctions list."
            rows={4}
            style={textarea}
          />
          <button type="button" onClick={compile} disabled={!instruction.trim() || submitting} style={button}>
            {submitting ? 'Compiling…' : 'Compile proposal'}
          </button>
          {compileError && <p style={{ ...copy, color: C.state.rejected }}>{compileError}</p>}
          {compilation && (
            <div style={{ marginTop: '16px' }}>
              <p style={{ ...kicker, color: compilation.status === 'proposal' ? C.state.approved : C.state.rejected }}>
                {compilation.status === 'proposal' ? 'PROPOSED — NOT ENACTED' : 'REFUSED'}
              </p>
              <p style={copy}>{compilation.reason}</p>
              {compilation.status === 'proposal' && compilation.after && (
                <>
                  <p style={kicker}>Rendered before / after</p>
                  <div style={comparison}>
                    <pre style={policyText}>{compilation.before.rendered}</pre>
                    <pre style={policyText}>{compilation.after.rendered}</pre>
                  </div>
                  {impact && (
                    <div style={confirmation}>
                      <p style={{ ...kicker, color: C.state.hypothetical }}>Human confirmation required</p>
                      <p style={{ ...copy, marginTop: 0, color: C.text.secondary }}>
                        Under this rule, {impact.impact.summary.changed} past decisions change, ${impact.impact.dollars.additional_held.toLocaleString()} additional held / ${impact.impact.dollars.released.toLocaleString()} released.
                      </p>
                      <div style={{ ...copy, marginBottom: '12px' }}>
                        Current: ${impact.impact.dollars.in_force_paid.toLocaleString()} paid · ${impact.impact.dollars.in_force_held.toLocaleString()} held<br />
                        Proposed: ${impact.impact.dollars.proposed_paid.toLocaleString()} paid · ${impact.impact.dollars.proposed_held.toLocaleString()} held
                      </div>
                      {impact.impact.changes.map((change) => (
                        <div key={change.payout_id} style={impactRow}>
                          <span style={{ fontFamily: MONO }}>{change.payout_id}</span>
                          <span>${change.amount.toLocaleString()}</span>
                          <span>{change.in_force.verdict} → {change.proposed.verdict}</span>
                          <span style={{ color: change.direction === 'additional_held' ? C.state.rejected : C.state.approved }}>{change.direction === 'additional_held' ? 'additional held' : 'released'}</span>
                        </div>
                      ))}
                      {!enacted ? (
                        <button
                          type="button"
                          style={enactButton}
                          onClick={async () => {
                            setSubmitting(true)
                            setCompileError(null)
                            try {
                              setEnacted(await api.enactPolicy(compilation.event_id))
                            } catch (err) {
                              setCompileError(err instanceof Error ? err.message : 'Unable to enact policy.')
                            } finally {
                              setSubmitting(false)
                            }
                          }}
                          disabled={submitting}
                        >
                          {submitting ? 'Enacting…' : 'Enact this policy'}
                        </button>
                      ) : <p style={{ ...copy, color: C.state.approved }}>Enacted {enacted.version} on {enacted.enacted}.</p>}
                    </div>
                  )}
                  {!impact && <p style={copy}>Select a recorded run to calculate the required impact before enactment.</p>}
                </>
              )}
            </div>
          )}
        </div>
      </Panel>

      {data.versions.map((v) => (
        <div key={v.version} style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <span style={{ fontFamily: MONO, fontSize: '13px', color: C.text.primary }}>{v.version}</span>
            {v.version === data.current && <span style={inForce}>IN FORCE</span>}
            <span style={{ fontFamily: MONO, fontSize: '11px', color: C.text.muted }}>enacted {v.enacted}</span>
          </div>
          <div style={{ ...copy, marginBottom: '12px', maxWidth: '700px' }}>{v.reason}</div>
          <Panel>
            <pre style={{ ...policyText, padding: '16px', background: C.bg.surface }}>{v.rendered}</pre>
          </Panel>
        </div>
      ))}

      <p style={{ ...copy, maxWidth: '700px' }}>{data.note}</p>
    </>
  )
}

const kicker = { fontFamily: MONO, fontSize: '10px', color: C.text.muted, letterSpacing: '0.08em', textTransform: 'uppercase' as const }
const copy = { fontFamily: SANS, fontSize: '12px', color: C.text.muted, lineHeight: 1.6 }
const textarea = { width: '100%', boxSizing: 'border-box' as const, resize: 'vertical' as const, fontFamily: SANS, fontSize: '13px', lineHeight: 1.5, color: C.text.primary, background: C.bg.elevated, border: `1px solid ${C.border.strong}`, borderRadius: '3px', padding: '10px', marginBottom: '10px' }
const button = { fontFamily: MONO, fontSize: '11px', color: C.bg.surface, background: C.text.primary, border: 0, borderRadius: '3px', padding: '8px 12px', cursor: 'pointer' }
const comparison = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '10px' }
const policyText = { fontFamily: MONO, fontSize: '11px', color: C.text.secondary, lineHeight: 1.6, margin: 0, padding: '12px', whiteSpace: 'pre-wrap' as const, overflowX: 'auto' as const, background: C.bg.elevated, border: `1px solid ${C.border.hairline}`, borderRadius: '3px' }
const inForce = { fontFamily: MONO, fontSize: '9px', color: C.state.approved, border: `1px solid ${C.state.approved}44`, background: `${C.state.approved}14`, borderRadius: '3px', padding: '2px 6px', letterSpacing: '0.08em' }
const confirmation = { marginTop: '14px', padding: '14px', background: '#EEF3F7', border: `1px dashed ${C.state.hypothetical}`, borderRadius: '4px' }
const impactRow = { display: 'grid', gridTemplateColumns: '90px 90px 1fr 120px', gap: '8px', fontFamily: MONO, fontSize: '10px', color: C.text.secondary, padding: '5px 0', borderTop: `1px solid ${C.border.hairline}` }
const enactButton = { fontFamily: MONO, fontSize: '11px', color: C.bg.surface, background: C.state.approved, border: 0, borderRadius: '3px', padding: '8px 12px', cursor: 'pointer' }
