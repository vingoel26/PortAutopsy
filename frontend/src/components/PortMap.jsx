import { useEventStream } from '../hooks/useEventStream';
import mockTraces from '../mock/traces.json';

const BERTHS = 4;
const CRANES_PER_BERTH = 6;
const CELL_W = 84;
const CELL_H = 52;
const MARGIN_LEFT = 36;
const MARGIN_TOP = 48; // extra top room for column labels

const CARGO_COLORS = {
  cold_chain: '#60a5fa', // blue
  hazmat:     '#f97316', // orange
  standard:   '#86efac', // green
};

const CARGO_BORDER = {
  cold_chain: '#2563eb',
  hazmat:     '#c2410c',
  standard:   '#16a34a',
};

/**
 * Derive cargo type from a trace event.
 * Real events: event.inputs.container.cargo_type
 * Fallback: infer from temperature_constraint presence
 */
function getCargoType(event) {
  const container = event?.inputs?.container;
  if (container?.cargo_type) return container.cargo_type;
  // Fallback inference if backend sends a flat inputs object
  if (event?.inputs?.temperature_constraint !== undefined) {
    return event.inputs.temperature_constraint !== null ? 'cold_chain' : 'standard';
  }
  return 'standard';
}

export default function PortMap() {
  const { events, connected } = useEventStream();

  // When WS is offline / no live events yet, fall back to mock data for testing
  const activeEvents = !connected && events.length === 0 ? mockTraces : events;

  // Build allocation map: crane_id → { agentId, cargoType }
  const allocations = {};
  activeEvents.forEach((e) => {
    if (e.output?.action === 'BID' && e.output?.slot) {
      allocations[e.output.slot] = {
        agentId:   e.agent_id,
        cargoType: getCargoType(e),
      };
    }
  });

  const svgW = MARGIN_LEFT + CRANES_PER_BERTH * CELL_W + 8;
  const svgH = MARGIN_TOP  + BERTHS * CELL_H + 8;

  return (
    <div>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, margin: 0 }}>Port Live View</h2>
        <span style={{ fontSize: 11, color: connected ? '#16a34a' : '#94a3b8' }}>
          {connected ? '● live' : '○ connecting'}
        </span>
        {/* Legend */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
          {Object.entries(CARGO_COLORS).map(([type, color]) => (
            <span key={type} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#64748b' }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: 'inline-block' }} />
              {type.replace('_', ' ')}
            </span>
          ))}
        </div>
      </div>

      <svg width={svgW} height={svgH} style={{ display: 'block' }}>
        {/* ── Crane column labels (C0 – C5) ── */}
        {Array.from({ length: CRANES_PER_BERTH }, (_, c) => (
          <text
            key={`col-${c}`}
            x={MARGIN_LEFT + c * CELL_W + (CELL_W - 4) / 2}
            y={MARGIN_TOP - 10}
            textAnchor="middle"
            fontSize={10}
            fontWeight={500}
            fill="#94a3b8"
          >
            C{c}
          </text>
        ))}

        {/* ── Grid cells ── */}
        {Array.from({ length: BERTHS }, (_, b) =>
          Array.from({ length: CRANES_PER_BERTH }, (_, c) => {
            const craneId    = `crane_${b * CRANES_PER_BERTH + c}`;
            const x          = MARGIN_LEFT + c * CELL_W;
            const y          = MARGIN_TOP  + b * CELL_H;
            const alloc      = allocations[craneId];
            const cargoType  = alloc?.cargoType || 'standard';
            const fillColor  = alloc ? CARGO_COLORS[cargoType] ?? CARGO_COLORS.standard : '#f1f5f9';
            const strokeClr  = alloc ? CARGO_BORDER[cargoType] ?? '#94a3b8'             : '#cbd5e1';

            return (
              <g key={craneId}>
                <rect
                  x={x + 2}
                  y={y + 2}
                  width={CELL_W - 6}
                  height={CELL_H - 6}
                  fill={fillColor}
                  fillOpacity={alloc ? 0.85 : 1}
                  stroke={strokeClr}
                  strokeWidth={alloc ? 1.5 : 0.5}
                  rx={5}
                />
                {alloc && (
                  <text
                    x={x + CELL_W / 2}
                    y={y + CELL_H / 2}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={9}
                    fontWeight={500}
                    fill="#1e293b"
                  >
                    {alloc.agentId.replace('container_', 'C')}
                  </text>
                )}
              </g>
            );
          })
        )}

        {/* ── Berth row labels (B0 – B3) ── */}
        {Array.from({ length: BERTHS }, (_, b) => (
          <text
            key={`row-${b}`}
            x={MARGIN_LEFT - 6}
            y={MARGIN_TOP + b * CELL_H + CELL_H / 2}
            textAnchor="end"
            dominantBaseline="central"
            fontSize={11}
            fontWeight={500}
            fill="#64748b"
          >
            B{b}
          </text>
        ))}
      </svg>
    </div>
  );
}
