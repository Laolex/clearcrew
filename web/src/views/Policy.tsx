import { api } from '../lib/api'
import { C, MONO, SANS } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'
import { Loading, Panel, SectionLabel } from '../components/Primitives'

export function Policy() {
  const { data, error } = useAsync(() => api.policies(), [])
  if (!data) return <Loading error={error} />

  return (
    <>
      <SectionLabel>The rules in force</SectionLabel>
      {data.versions.map((v) => (
        <div key={v.version} style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <span style={{ fontFamily: MONO, fontSize: '13px', color: C.text.primary }}>
              {v.version}
            </span>
            {v.version === data.current && (
              <span
                style={{
                  fontFamily: MONO,
                  fontSize: '9px',
                  color: C.state.approved,
                  border: `1px solid ${C.state.approved}44`,
                  background: `${C.state.approved}14`,
                  borderRadius: '3px',
                  padding: '2px 6px',
                  letterSpacing: '0.08em',
                }}
              >
                IN FORCE
              </span>
            )}
            <span style={{ fontFamily: MONO, fontSize: '11px', color: C.text.muted }}>
              enacted {v.enacted}
            </span>
          </div>

          <div
            style={{
              fontFamily: SANS,
              fontSize: '12px',
              color: C.text.muted,
              marginBottom: '12px',
              maxWidth: '700px',
            }}
          >
            {v.reason}
          </div>

          {/* The binding text, exactly as both the society and the baseline
              received it. Paraphrasing the policy here would make this page a
              second source of truth, and there can only be one. */}
          <Panel>
            <pre
              style={{
                fontFamily: MONO,
                fontSize: '12px',
                color: C.text.secondary,
                lineHeight: 1.7,
                margin: 0,
                padding: '16px',
                whiteSpace: 'pre-wrap',
                overflowX: 'auto',
              }}
            >
              {v.rendered}
            </pre>
          </Panel>
        </div>
      ))}

      <p
        style={{
          fontFamily: SANS,
          fontSize: '12px',
          color: C.text.muted,
          maxWidth: '700px',
          lineHeight: 1.6,
        }}
      >
        {data.note}
      </p>
    </>
  )
}
