import { useState, useEffect } from 'react';
import mockTraces from '../mock/traces.json';
import { useEventStream } from '../hooks/useEventStream';

const isFailure = (e) => {
  const out = JSON.stringify(e.output ?? {}).toLowerCase();
  const eff = JSON.stringify(Array.isArray(e.downstream_effects) ? e.downstream_effects : []).toLowerCase();
  return out.includes('violation') || out.includes('dropped') ||
    eff.includes('violation') || eff.includes('cold_chain');
};

const getCargoType = (e) => e?.inputs?.container?.cargo_type ?? 'standard';
const getAction    = (e) => e?.output?.action ?? '—';

const CARGO_COLOR = {
  cold_chain: '#67E8F9',
  hazmat:     '#FCD34D',
  standard:   '#2DD4BF',
};

export default function AgentTimeline({ apiUrl = 'http://localhost:8000/traces' }) {
  const [restTraces, setRestTraces] = useState([]);
  const [selected, setSelected]     = useState(null);
  const { events: wsEvents }        = useEventStream();

  useEffect(() => {
    fetch(apiUrl)
      .then(r => r.json())
      .then(d => { if (d?.length) setRestTraces(d); })
      .catch(() => {});
  }, [apiUrl]);

  const allTraces = (() => {
    const merged = [...restTraces, ...wsEvents];
    if (merged.length === 0) return mockTraces;
    const seen = new Set();
    return merged.filter(t => {
      if (seen.has(t.trace_id)) return false;
      seen.add(t.trace_id); return true;
    });
  })();

  const failCount = allTraces.filter(isFailure).length;

  return (
    <>
      {/* Header */}
      <div className="section-header" style={{ marginBottom: 10 }}>
        <span className="section-title-dark">Telemetry Log</span>
        <span className="tag tag-dark">{allTraces.length} Events</span>
        {failCount > 0 && <span className="tag tag-red">{failCount} Errors</span>}
      </div>

      {/* Event rows */}
      <div className="telemetry-body">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Agent', 'Action', 'Slot', 'Cargo', 'Round', 'Status'].map(h => (
                <th key={h} style={{
                  textAlign: 'left', padding: '0 10px 6px',
                  fontSize: 10, fontWeight: 600,
                  textTransform: 'uppercase', letterSpacing: '0.08em',
                  color: 'var(--tw3)',
                  borderBottom: '1px solid rgba(255,255,255,0.06)',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allTraces.slice(0, 30).map((e, i) => {
              const fail  = isFailure(e);
              const cargo = getCargoType(e);
              const color = CARGO_COLOR[cargo] ?? '#2DD4BF';
              const isSel = selected?.trace_id === e.trace_id;
              return (
                <tr
                  key={e.trace_id}
                  onClick={() => setSelected(isSel ? null : e)}
                  style={{
                    cursor: 'pointer',
                    background: isSel ? 'rgba(255,255,255,0.04)' : 'transparent',
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    transition: 'background 0.12s',
                  }}
                >
                  {/* Agent ID */}
                  <td style={{ padding: '6px 10px', fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--tw2)', whiteSpace: 'nowrap' }}>
                    {e.agent_id?.replace('container_', 'CN-')}
                  </td>
                  {/* Action */}
                  <td style={{ padding: '6px 10px', fontSize: 11, color: 'var(--tw1)', fontWeight: 500 }}>
                    {getAction(e)}
                  </td>
                  {/* Slot */}
                  <td style={{ padding: '6px 10px', fontSize: 10, color: 'var(--tw3)', fontFamily: 'var(--mono)' }}>
                    {e.output?.slot ?? '—'}
                  </td>
                  {/* Cargo type dot */}
                  <td style={{ padding: '6px 10px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
                      <span style={{ fontSize: 10, color: 'var(--tw3)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        {cargo === 'cold_chain' ? 'COLD' : cargo === 'hazmat' ? 'HMZT' : 'STD'}
                      </span>
                    </span>
                  </td>
                  {/* Round */}
                  <td style={{ padding: '6px 10px', fontSize: 10, color: 'var(--tw3)', fontFamily: 'var(--mono)' }}>
                    {e.round ?? '—'}
                  </td>
                  {/* Status badge */}
                  <td style={{ padding: '6px 10px' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      fontSize: 10, fontWeight: 600,
                      color: fail ? 'var(--rose)' : 'var(--teal)',
                      background: fail ? 'rgba(251,113,133,0.08)' : 'rgba(45,212,191,0.08)',
                      border: `1px solid ${fail ? 'rgba(251,113,133,0.2)' : 'rgba(45,212,191,0.2)'}`,
                      borderRadius: 4, padding: '1px 7px',
                    }}>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', background: fail ? 'var(--rose)' : 'var(--teal)' }} />
                      {fail ? 'ERR' : 'OK'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* Expanded inspector row */}
        {selected && (
          <div style={{
            margin: '8px 0',
            padding: '12px 14px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 'var(--r-sm)',
            display: 'flex', gap: 24, flexWrap: 'wrap',
          }}>
            <div>
              <div className="info-label info-label-dark">Agent</div>
              <span style={{ fontSize: 12, fontFamily: 'var(--mono)', color: '#2DD4BF' }}>
                {selected.agent_id?.replace('container_', 'CN-')}
              </span>
            </div>
            <div>
              <div className="info-label info-label-dark">Seq</div>
              <span style={{ fontSize: 12, color: 'var(--tw2)' }}>{selected.round}</span>
            </div>
            <div style={{ flex: 1 }}>
              <div className="info-label info-label-dark">Chain of Thought</div>
              <p style={{ fontSize: 11, color: 'var(--tw3)', lineHeight: 1.5, margin: 0 }}>
                {selected.chain_of_thought || <span style={{ opacity: 0.4 }}>No trace data</span>}
              </p>
            </div>
            {selected.duration_ms && (
              <div>
                <div className="info-label info-label-dark">Duration</div>
                <span style={{ fontSize: 12, color: '#67E8F9', fontFamily: 'var(--mono)' }}>
                  {selected.duration_ms.toFixed(1)}ms
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
