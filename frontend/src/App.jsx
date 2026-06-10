import { useState } from 'react';
import './App.css';
import PortMap from './components/PortMap';
import AgentTimeline from './components/AgentTimeline';
import MetricsPanel from './components/MetricsPanel';
import AutopsyPanel from './components/AutopsyPanel';

export default function App() {
  const [showFixed, setShowFixed] = useState(false);

  return (
    <>
      {/* ── Background layer ── */}
      <div className="bg-layer" />

      {/* ── Navbar ── */}
      <nav className="navbar">
        <div className="navbar-logo">
          <div className="navbar-logo-icon">⚓</div>
          PortAutopsy
        </div>
        <div className="navbar-sep" />
        <span className="tag tag-gray">v1.0</span>
        <div className="navbar-end">
          <div className="live-pill">
            <div className="status-dot live" />
            Live System
          </div>
          <span className="tag tag-blue">Agents: 200</span>
          <span className="tag tag-mint">Scenarios: 3</span>
        </div>
      </nav>

      {/* ── Two-column layout ── */}
      <div className="layout">

        {/* LEFT: PortMap + Telemetry stacked */}
        <div className="col-left">

          {/* Port Map — fills upper space */}
          <div className="card portmap-card">
            <PortMap />
          </div>

          {/* Telemetry Log — fixed height, scrollable */}
          <div className="card-dark telemetry-card">
            <AgentTimeline />
          </div>

        </div>

        {/* RIGHT: Metrics then Autopsy, scrollable column */}
        <div className="col-right">
          <div className="card metrics-card">
            <MetricsPanel showFixed={showFixed} />
          </div>
          <div className="card autopsy-card">
            <AutopsyPanel onReportLoaded={() => setShowFixed(true)} />
          </div>
        </div>

      </div>
    </>
  );
}
