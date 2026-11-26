import React from 'react';

const SCENARIOS = [
  { id: 'ALL', label: 'All Scenarios' },
  { id: 'NORMAL_BASELINE', label: 'Normal Baseline' },
  { id: 'ELEVATED_COGNITIVE_WORKLOAD', label: 'Elevated Workload' },
  { id: 'FATIGUE_PHYSIOLOGICAL', label: 'Physiological Fatigue' },
  { id: 'DEGRADED_SIGNAL_QUALITY', label: 'Degraded Signal' },
  { id: 'MIXED_OPERATIONAL_CONDITIONS', label: 'Mixed Operational' },
];

export function DatasetBrowser({
  sessions,
  selectedSessionId,
  onSelectSession,
  scenarioFilter,
  onSelectScenario,
  participantsMap,
  isLoading,
}) {
  const filteredSessions = scenarioFilter === 'ALL'
    ? sessions
    : sessions.filter(s => s.scenario === scenarioFilter);

  return (
    <div className="research-card dataset-browser-card">
      <div className="card-header-clean">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="research-badge-accent">DATASET EXPLORER</span>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Synthetic Sortie Registry</h3>
        </div>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {filteredSessions.length} of {sessions.length} Sessions Available
        </span>
      </div>

      {/* Scenario Filter Chips */}
      <div className="scenario-filter-bar">
        {SCENARIOS.map(sc => (
          <button
            key={sc.id}
            className={`scenario-chip ${scenarioFilter === sc.id ? 'active' : ''}`}
            onClick={() => onSelectScenario(sc.id)}
          >
            {sc.label}
          </button>
        ))}
      </div>

      {/* Session Selection Grid / List */}
      <div className="session-grid-container">
        {isLoading ? (
          <div className="research-loading-state">
            <div className="spinner-subtle" />
            <span>Loading Synthetic Session Registry...</span>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="research-empty-state">
            <span>No sessions match the selected scenario filter.</span>
          </div>
        ) : (
          filteredSessions.map(session => {
            const isSelected = session.session_id === selectedSessionId;
            const participant = participantsMap[session.participant_id] || {};
            
            return (
              <div
                key={session.session_id}
                className={`session-card-item ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectSession(session.session_id)}
                role="button"
                tabIndex={0}
              >
                <div className="session-card-top">
                  <span className="session-id-tag">{session.session_id}</span>
                  <span className={`scenario-tag-badge ${session.scenario.toLowerCase()}`}>
                    {session.scenario.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="session-card-pilot">
                  <strong>{session.participant_id}</strong>
                  <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                    {participant.callsign || 'PILOT'} (Age {participant.age || '—'})
                  </span>
                </div>

                <div className="session-card-metrics">
                  <div className="metric-col">
                    <span className="label">Resting HR</span>
                    <span className="val">{session.baseline_resting_hr || participant.resting_heart_rate || '—'} bpm</span>
                  </div>
                  <div className="metric-col">
                    <span className="label">Base RMSSD</span>
                    <span className="val">{session.baseline_rmssd || participant.baseline_rmssd || '—'} ms</span>
                  </div>
                  <div className="metric-col">
                    <span className="label">Drop Rate</span>
                    <span className="val" style={{ color: session.missing_rate_pct > 10 ? 'var(--color-alert)' : 'inherit' }}>
                      {session.missing_rate_pct}%
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default DatasetBrowser;
