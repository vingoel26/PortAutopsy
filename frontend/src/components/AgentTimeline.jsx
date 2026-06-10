import { useState, useEffect } from 'react';
import mockTraces from '../mock/traces.json';

const isFailureEvent = (e) => {
  const str = JSON.stringify(e.output || {}) + JSON.stringify(e.downstream_effects || {});
  return str.toLowerCase().includes('violation') || str.toLowerCase().includes('dropped');
};

export default function AgentTimeline({ apiUrl = 'http://localhost:8000/traces' }) {
  const [traces, setTraces] = useState(mockTraces);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetch(apiUrl)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.length > 0) setTraces(data);
      })
      .catch(() => {
        // Fallback to mock traces if the server isn't up
        setTraces(mockTraces);
      });
  }, [apiUrl]);

  const byAgent = traces.reduce((acc, t) => {
    if (!acc[t.agent_id]) acc[t.agent_id] = [];
    acc[t.agent_id].push(t);
    return acc;
  }, {});

  return (
    <div style={{ display: 'flex', gap: 12 }}>
      <div style={{ flex: 1, overflowX: 'auto' }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Agent Timeline</h2>
        {Object.entries(byAgent).slice(0, 20).map(([agent, events]) => (
          <div key={agent} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
            <span style={{ fontSize: 10, width: 90, flexShrink: 0, color: '#64748b' }}>{agent}</span>
            <div style={{ display: 'flex', gap: 2 }}>
              {events.map((e) => {
                const failed = isFailureEvent(e);
                const isSelected = selected?.trace_id === e.trace_id;
                
                let bg;
                if (failed) bg = isSelected ? '#dc2626' : '#fca5a5';
                else bg = isSelected ? '#3b82f6' : '#93c5fd';

                return (
                  <div
                    key={e.trace_id}
                    onClick={() => setSelected(e)}
                    style={{
                      width: 12,
                      height: 20,
                      borderRadius: 2,
                      cursor: 'pointer',
                      background: bg,
                    }}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {selected && (
        <div
          style={{
            width: 260,
            padding: 12,
            background: '#f8fafc',
            borderRadius: 8,
            border: '0.5px solid #e2e8f0',
            fontSize: 12,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 6 }}>
            {selected.agent_id} · r{selected.round}
          </div>
          <div style={{ color: '#64748b', marginBottom: 4 }}>Chain of thought:</div>
          <div style={{ marginBottom: 8 }}>{selected.chain_of_thought || '—'}</div>
          <div style={{ color: '#64748b', marginBottom: 4 }}>Output:</div>
          <pre style={{ fontSize: 11, overflow: 'auto' }}>
            {JSON.stringify(selected.output, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
