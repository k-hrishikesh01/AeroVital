import React, { useState, useEffect } from 'react';
import researchApi from '../../services/researchApi';

// The canonical five representative sessions from the AeroVital synthetic dataset v1
const CANONICAL_SCENARIOS = [
  {
    id: 'NORMAL_BASELINE',
    name: 'Normal Baseline Flight',
    sessionId: 'SYN-S001',
    participantId: 'SYN-P001',
    color: 'var(--color-normal)',
    description: 'Routine cruise flight under nominal conditions. Stable autonomic regulation with low sympathetic arousal.',
    expectedState: 'NORMAL',
  },
  {
    id: 'ELEVATED_COGNITIVE_WORKLOAD',
    name: 'Elevated Cognitive Workload',
    sessionId: 'SYN-S013',
    participantId: 'SYN-P007',
    color: 'var(--color-warning)',
    description: 'Complex instrument approaches, ATC rerouting, and multi-tasking demand. Elevated heart rate and suppressed HRV.',
    expectedState: 'COGNITIVE_WORKLOAD',
  },
  {
    id: 'FATIGUE_PHYSIOLOGICAL',
    name: 'Physiological Fatigue',
    sessionId: 'SYN-S025',
    participantId: 'SYN-P013',
    color: 'var(--color-alert)',
    description: 'Extended flight duration with circadian trough. Drift in baseline tone, reduced vagal index, and intermittent micro-lapses.',
    expectedState: 'FATIGUE',
  },
  {
    id: 'DEGRADED_SIGNAL_QUALITY',
    name: 'Degraded Signal Quality',
    sessionId: 'SYN-S037',
    participantId: 'SYN-P019',
    color: 'var(--color-insufficient)',
    description: 'Sensor displacement, excessive motion artifacts, and low perfusion. SQI drops below 0.50 triggering deterministic abstention.',
    expectedState: 'INSUFFICIENT_DATA',
  },
  {
    id: 'MIXED_OPERATIONAL_CONDITIONS',
    name: 'Mixed Operational Conditions',
    sessionId: 'SYN-S049',
    participantId: 'SYN-P025',
    color: 'var(--color-cyan)',
    description: 'Dynamic mission switching between baseline flight, turbulent maneuvers, peak mental workload, and recovery periods.',
    expectedState: 'MIXED',
  },
];

export function PresentationMode({ onClose, onSelectSession }) {
  const [scenarioRuns, setScenarioRuns] = useState({});
  const [selectedScenarioId, setSelectedScenarioId] = useState('NORMAL_BASELINE');
  const [isExecutingAll, setIsExecutingAll] = useState(false);
  const [executingScenario, setExecutingScenario] = useState(null);
  const [selectedTimeseries, setSelectedTimeseries] = useState([]);
  const [isLoadingTimeseries, setIsLoadingTimeseries] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Load latest runs for all 5 canonical scenarios on mount
  useEffect(() => {
    loadAllScenarioRuns();
  }, []);

  // When selected scenario changes, stream its downsampled timeseries
  useEffect(() => {
    const sc = CANONICAL_SCENARIOS.find(s => s.id === selectedScenarioId);
    if (sc) {
      loadTimeseriesForScenario(sc.sessionId);
    }
  }, [selectedScenarioId]);

  const loadAllScenarioRuns = async () => {
    try {
      const runsMap = {};
      await Promise.all(
        CANONICAL_SCENARIOS.map(async (sc) => {
          try {
            const runs = await researchApi.getRuns({ session: sc.sessionId, limit: 1 });
            if (runs && runs.length > 0) {
              const fullRun = await researchApi.getRun(runs[0].run_id);
              runsMap[sc.id] = fullRun;
            }
          } catch (e) {
            console.warn(`Could not load run for ${sc.sessionId}:`, e.message);
          }
        })
      );
      setScenarioRuns(runsMap);
    } catch (err) {
      setErrorMessage(`Failed to load historical scenario runs: ${err.message}`);
    }
  };

  const loadTimeseriesForScenario = async (sessionId) => {
    setIsLoadingTimeseries(true);
    try {
      const resp = await researchApi.getSessionTimeseries(sessionId, 10);
      setSelectedTimeseries(resp?.data || []);
    } catch (e) {
      console.warn(`Timeseries load failed for ${sessionId}:`, e.message);
      setSelectedTimeseries([]);
    } finally {
      setIsLoadingTimeseries(false);
    }
  };

  const executeSingleScenario = async (sc) => {
    setExecutingScenario(sc.id);
    setErrorMessage(null);
    try {
      const run = await researchApi.executeSession(sc.sessionId, `Presentation execution for ${sc.name}`);
      setScenarioRuns(prev => ({ ...prev, [sc.id]: run }));
      if (sc.id === selectedScenarioId) {
        loadTimeseriesForScenario(sc.sessionId);
      }
    } catch (err) {
      setErrorMessage(`Execution failed for ${sc.name}: ${err.message}`);
    } finally {
      setExecutingScenario(null);
    }
  };

  const executeAllScenarios = async () => {
    setIsExecutingAll(true);
    setErrorMessage(null);
    try {
      for (const sc of CANONICAL_SCENARIOS) {
        setExecutingScenario(sc.id);
        const run = await researchApi.executeSession(sc.sessionId, `Batch presentation run for ${sc.name}`);
        setScenarioRuns(prev => ({ ...prev, [sc.id]: run }));
      }
      // Reload current timeseries
      const current = CANONICAL_SCENARIOS.find(s => s.id === selectedScenarioId);
      if (current) {
        loadTimeseriesForScenario(current.sessionId);
      }
    } catch (err) {
      setErrorMessage(`Batch execution error: ${err.message}`);
    } finally {
      setIsExecutingAll(false);
      setExecutingScenario(null);
    }
  };

  const exportSummaryCsv = () => {
    const headers = [
      'Scenario',
      'Session ID',
      'Participant ID',
      'Total Samples',
      'Windows Evaluated',
      'Execution Duration (s)',
      'Throughput (smp/s)',
      'Mean Confidence',
      'Mean SQI',
      'Abstention Rate (%)',
      'Normal (%)',
      'Cognitive Workload (%)',
      'Fatigue (%)',
      'Insufficient Data (%)',
    ];

    const rows = CANONICAL_SCENARIOS.map(sc => {
      const run = scenarioRuns[sc.id];
      const sb = run?.state_breakdown || {};
      return [
        `"${sc.name}"`,
        sc.sessionId,
        sc.participantId,
        run?.total_samples_processed ?? 3600,
        run?.total_windows_evaluated ?? 0,
        run?.execution_duration_sec ?? 0,
        run?.throughput_samples_per_sec ?? 0,
        run?.mean_confidence ?? '—',
        run?.mean_sqi ?? '—',
        run?.abstention_rate_pct ?? '—',
        sb.NORMAL?.percentage ?? 0,
        sb.COGNITIVE_WORKLOAD?.percentage ?? 0,
        sb.FATIGUE?.percentage ?? 0,
        sb.INSUFFICIENT_DATA?.percentage ?? 0,
      ].join(',');
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `aerovital_five_scenario_evaluation_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const activeScenario = CANONICAL_SCENARIOS.find(s => s.id === selectedScenarioId);
  const activeRun = scenarioRuns[selectedScenarioId];

  return (
    <div className="presentation-mode-overlay">
      {/* Top Presentation Control Bar */}
      <header className="presentation-header-bar">
        <div className="presentation-brand-group">
          <span className="presentation-live-badge">📊 RESEARCH DEMONSTRATION MODE</span>
          <h1 className="presentation-title">AeroVital Physiological Intelligence — Five-Scenario Evaluation</h1>
          <span className="presentation-version-pill">AeroVitalPipeline v1.0.0 | Synthetic Dataset v1</span>
        </div>

        <div className="presentation-actions-group">
          <button
            type="button"
            className="btn-secondary"
            onClick={exportSummaryCsv}
            title="Export 5-Scenario Comparison Table as CSV"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            <span>Export CSV</span>
          </button>

          <button
            type="button"
            className="btn-primary"
            onClick={executeAllScenarios}
            disabled={isExecutingAll || executingScenario !== null}
            title="Execute AeroVitalPipeline sequentially across all 5 benchmark sessions"
          >
            {isExecutingAll ? (
              <>
                <div className="spinner-subtle inline" />
                <span>Evaluating Scenarios...</span>
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                <span>Execute All 5 Scenarios</span>
              </>
            )}
          </button>

          <button
            type="button"
            className="btn-icon presentation-close-btn"
            onClick={onClose}
            title="Exit Presentation Mode and Return to Workbench"
            aria-label="Close Presentation Mode"
          >
            &times;
          </button>
        </div>
      </header>

      {/* Scientific Integrity Disclosure Ribbon */}
      <div className="presentation-integrity-ribbon">
        <div className="integrity-icon">⚠️</div>
        <div className="integrity-content">
          <strong>SCIENTIFIC INTEGRITY & EVALUATION DISCLOSURES:</strong>
          <span>
            All telemetry is derived from the deterministic <strong>AeroVital Synthetic Physiological Dataset v1</strong> (216,000 observations; 30 participants; 60 sorties).
            Classifications reflect the provisional rule-based <strong>AeroVitalPipeline</strong> (HR/HRV autonomic tone + accelerometer kinematics).
            <strong> No real pilot ground truth is claimed.</strong> Confidence scores represent heuristic rule-agreement indices.
            <strong> Workload/Fatigue overlap is preserved</strong> reflecting biological autonomic co-activation under prolonged demand.
            SpO₂, skin temperature, and ECG are <strong>uninstrumented (null / unavailable)</strong> and never fabricated.
          </span>
        </div>
      </div>

      {errorMessage && (
        <div className="research-error-banner" style={{ margin: '12px 24px 0' }}>
          <span>{errorMessage}</span>
          <button className="dismiss-btn" onClick={() => setErrorMessage(null)}>&times;</button>
        </div>
      )}

      {/* Main Presentation View Container */}
      <div className="presentation-body-container">
        {/* Section 1: Five-Scenario High-Level Comparative Matrix */}
        <section className="presentation-matrix-card">
          <div className="card-header-flex">
            <div>
              <h2 className="section-heading">Five-Scenario Comparative Performance Matrix</h2>
              <p className="section-subtext">Direct benchmark comparison across all 5 operational mission scenarios evaluated by AeroVitalPipeline.</p>
            </div>
            <div className="matrix-status-meta">
              <span>Evaluated: <strong>{Object.keys(scenarioRuns).length} / 5 Scenarios</strong></span>
            </div>
          </div>

          <div className="presentation-table-wrapper">
            <table className="presentation-matrix-table">
              <thead>
                <tr>
                  <th>Scenario & Mission Phase</th>
                  <th>Session & Subject</th>
                  <th>Samples / Windows</th>
                  <th>Runtime & Throughput</th>
                  <th>Mean Conf</th>
                  <th>Mean SQI</th>
                  <th>Abstention</th>
                  <th>Primary State Classification Breakdown</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {CANONICAL_SCENARIOS.map(sc => {
                  const run = scenarioRuns[sc.id];
                  const isCurrent = sc.id === selectedScenarioId;
                  const isRunning = executingScenario === sc.id;
                  const sb = run?.state_breakdown || {};

                  return (
                    <tr
                      key={sc.id}
                      className={`${isCurrent ? 'active-row' : ''}`}
                      onClick={() => setSelectedScenarioId(sc.id)}
                    >
                      <td className="scenario-col">
                        <div className="sc-indicator-dot" style={{ backgroundColor: sc.color }} />
                        <div>
                          <strong className="sc-name">{sc.name}</strong>
                          <span className="sc-desc-line">{sc.description.slice(0, 75)}...</span>
                        </div>
                      </td>

                      <td className="session-col mono-num">
                        <strong>{sc.sessionId}</strong>
                        <span className="sub-val">{sc.participantId}</span>
                      </td>

                      <td className="samples-col mono-num">
                        {run ? (
                          <>
                            <strong>{run.total_samples_processed.toLocaleString()} smp</strong>
                            <span className="sub-val">{run.total_windows_evaluated.toLocaleString()} win</span>
                          </>
                        ) : (
                          <span className="sub-val">3,600 smp (pending)</span>
                        )}
                      </td>

                      <td className="perf-col mono-num">
                        {run ? (
                          <>
                            <strong className="throughput-text">
                              {Number(run.throughput_samples_per_sec).toLocaleString()} smp/s
                            </strong>
                            <span className="sub-val">{run.execution_duration_sec}s runtime</span>
                          </>
                        ) : (
                          <span className="sub-val">—</span>
                        )}
                      </td>

                      <td className="conf-col mono-num">
                        {run?.mean_confidence != null ? (
                          <span className="metric-pill conf-pill">{run.mean_confidence}</span>
                        ) : (
                          <span className="sub-val">—</span>
                        )}
                      </td>

                      <td className="sqi-col mono-num">
                        {run?.mean_sqi != null ? (
                          <span className={`metric-pill ${run.mean_sqi >= 0.70 ? 'sqi-good' : 'sqi-bad'}`}>
                            {run.mean_sqi}
                          </span>
                        ) : (
                          <span className="sub-val">—</span>
                        )}
                      </td>

                      <td className="abstain-col mono-num">
                        {run ? (
                          <strong className={run.abstention_rate_pct > 50 ? 'abstain-high' : 'abstain-low'}>
                            {run.abstention_rate_pct}%
                          </strong>
                        ) : (
                          <span className="sub-val">—</span>
                        )}
                      </td>

                      <td className="state-dist-col">
                        {run ? (
                          <div className="state-stacked-bar">
                            {sb.NORMAL?.percentage > 0 && (
                              <div
                                className="bar-seg normal"
                                style={{ width: `${sb.NORMAL.percentage}%` }}
                                title={`Normal: ${sb.NORMAL.percentage}%`}
                              />
                            )}
                            {sb.COGNITIVE_WORKLOAD?.percentage > 0 && (
                              <div
                                className="bar-seg workload"
                                style={{ width: `${sb.COGNITIVE_WORKLOAD.percentage}%` }}
                                title={`Cognitive Workload: ${sb.COGNITIVE_WORKLOAD.percentage}%`}
                              />
                            )}
                            {sb.FATIGUE?.percentage > 0 && (
                              <div
                                className="bar-seg fatigue"
                                style={{ width: `${sb.FATIGUE.percentage}%` }}
                                title={`Fatigue: ${sb.FATIGUE.percentage}%`}
                              />
                            )}
                            {sb.INSUFFICIENT_DATA?.percentage > 0 && (
                              <div
                                className="bar-seg insufficient"
                                style={{ width: `${sb.INSUFFICIENT_DATA.percentage}%` }}
                                title={`Insufficient Data: ${sb.INSUFFICIENT_DATA.percentage}%`}
                              />
                            )}
                          </div>
                        ) : (
                          <span className="sub-val">Awaiting execution</span>
                        )}
                        {run && (
                          <div className="state-pct-labels">
                            {sb.NORMAL?.percentage > 0 && <span>NORM {sb.NORMAL.percentage}%</span>}
                            {sb.COGNITIVE_WORKLOAD?.percentage > 0 && <span>WORK {sb.COGNITIVE_WORKLOAD.percentage}%</span>}
                            {sb.FATIGUE?.percentage > 0 && <span>FATG {sb.FATIGUE.percentage}%</span>}
                            {sb.INSUFFICIENT_DATA?.percentage > 0 && <span>ABST {sb.INSUFFICIENT_DATA.percentage}%</span>}
                          </div>
                        )}
                      </td>

                      <td className="actions-col">
                        <button
                          type="button"
                          className="btn-tiny"
                          onClick={(e) => {
                            e.stopPropagation();
                            executeSingleScenario(sc);
                          }}
                          disabled={isRunning || isExecutingAll}
                        >
                          {isRunning ? 'Running...' : run ? 'Re-run' : 'Execute'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 2: Deep-Dive Scenario Inspector */}
        <section className="presentation-detail-card">
          <div className="detail-header-tabs">
            {CANONICAL_SCENARIOS.map(sc => (
              <button
                key={sc.id}
                type="button"
                className={`scenario-tab-btn ${sc.id === selectedScenarioId ? 'active' : ''}`}
                onClick={() => setSelectedScenarioId(sc.id)}
              >
                <span className="dot" style={{ backgroundColor: sc.color }} />
                <span>{sc.name}</span>
                <span className="tab-session-tag">{sc.sessionId}</span>
              </button>
            ))}
          </div>

          <div className="scenario-detail-content">
            <div className="detail-meta-banner">
              <div>
                <h3 className="detail-title">{activeScenario?.name} ({activeScenario?.sessionId})</h3>
                <p className="detail-sub">{activeScenario?.description}</p>
              </div>

              {activeRun && (
                <div className="detail-stats-cluster">
                  <div className="stat-box">
                    <span className="lbl">Throughput</span>
                    <span className="val mono-num">{Number(activeRun.throughput_samples_per_sec).toLocaleString()} /s</span>
                  </div>
                  <div className="stat-box">
                    <span className="lbl">Mean Confidence</span>
                    <span className="val mono-num">{activeRun.mean_confidence ?? '—'}</span>
                  </div>
                  <div className="stat-box">
                    <span className="lbl">Mean SQI</span>
                    <span className="val mono-num">{activeRun.mean_sqi ?? '—'}</span>
                  </div>
                  <div className="stat-box">
                    <span className="lbl">Abstention Rate</span>
                    <span className="val mono-num">{activeRun.abstention_rate_pct}%</span>
                  </div>
                </div>
              )}
            </div>

            {/* Synchronized Timeseries Visualization for this scenario */}
            <div className="presentation-charts-grid">
              <div className="chart-panel">
                <div className="panel-title-row">
                  <span className="panel-heading">HEART RATE & INTER-BEAT INTERVAL (RR)</span>
                  <span className="panel-badge">Actual Synthetic Telemetry (Downsampled 10x)</span>
                </div>

                {isLoadingTimeseries ? (
                  <div className="chart-loading-state">
                    <div className="spinner-subtle" />
                    <span>Streaming timeseries points...</span>
                  </div>
                ) : selectedTimeseries.length > 0 ? (
                  <div className="presentation-timeseries-view">
                    <svg className="presentation-svg-chart" viewBox="0 0 1000 220" preserveAspectRatio="none">
                      {/* Grid lines */}
                      <line x1="0" y1="44" x2="1000" y2="44" stroke="var(--chart-grid)" strokeDasharray="4 4" />
                      <line x1="0" y1="88" x2="1000" y2="88" stroke="var(--chart-grid)" strokeDasharray="4 4" />
                      <line x1="0" y1="132" x2="1000" y2="132" stroke="var(--chart-grid)" strokeDasharray="4 4" />
                      <line x1="0" y1="176" x2="1000" y2="176" stroke="var(--chart-grid)" strokeDasharray="4 4" />

                      {/* Heart Rate Path (scaled 40 to 140 bpm) */}
                      {(() => {
                        const pts = selectedTimeseries.map((d, i) => {
                          const x = (i / (selectedTimeseries.length - 1)) * 1000;
                          const hr = Math.max(40, Math.min(140, d.heart_rate || 70));
                          const y = 200 - ((hr - 40) / 100) * 180;
                          return `${x},${y}`;
                        }).join(' ');
                        return <polyline points={pts} fill="none" stroke="var(--chart-hr)" strokeWidth="2.5" />;
                      })()}
                    </svg>

                    <div className="chart-legend-row">
                      <span className="legend-item"><span className="legend-dot hr-dot" /> Heart Rate (bpm)</span>
                      <span className="legend-item channel-null">SpO₂: Null (Uninstrumented)</span>
                      <span className="legend-item channel-null">Skin Temp: Null (Uninstrumented)</span>
                      <span className="legend-item channel-null">ECG: Unavailable</span>
                    </div>
                  </div>
                ) : (
                  <div className="chart-empty-state">
                    <span>No timeseries data loaded. Click 'Execute' to run this session.</span>
                  </div>
                )}
              </div>

              {/* State Timeline Breakdown */}
              <div className="chart-panel">
                <div className="panel-title-row">
                  <span className="panel-heading">CLASSIFICATION TIMELINE & CONFIDENCE</span>
                  <span className="panel-badge">AeroVitalPipeline Evaluation Windows</span>
                </div>

                {activeRun?.window_outputs && activeRun.window_outputs.length > 0 ? (
                  <div className="presentation-timeline-view">
                    <div className="presentation-timeline-bar">
                      {activeRun.window_outputs.map((w, idx) => {
                        const st = (w.state || 'UNKNOWN').toLowerCase();
                        return (
                          <div
                            key={idx}
                            className={`timeline-window-slice ${st}`}
                            title={`T+${w.timestamp}s | State: ${w.state} | Conf: ${w.confidence} | SQI: ${w.sqi}`}
                          />
                        );
                      })}
                    </div>

                    <div className="timeline-legend-row">
                      <span className="legend-item"><span className="legend-dot normal" /> Normal</span>
                      <span className="legend-item"><span className="legend-dot workload" /> Cognitive Workload</span>
                      <span className="legend-item"><span className="legend-dot fatigue" /> Fatigue</span>
                      <span className="legend-item"><span className="legend-dot insufficient" /> Insufficient Signal</span>
                    </div>

                    {/* Dominant Diagnostic Factors Summary */}
                    <div className="dominant-factors-panel">
                      <strong className="factors-title">Dominant Contributing Diagnostic Factors:</strong>
                      <div className="factors-chips-row">
                        {activeRun.dominant_factors_summary && activeRun.dominant_factors_summary.length > 0 ? (
                          activeRun.dominant_factors_summary.slice(0, 4).map((f, i) => (
                            <div key={i} className="factor-chip">
                              <span className="fname">{f.factor.replace(/_/g, ' ')}</span>
                              <span className="fcount">({f.occurrences} windows)</span>
                            </div>
                          ))
                        ) : (
                          <span className="sub-val">No dominant factors isolated</span>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="chart-empty-state">
                    <span>Session not yet evaluated. Click 'Execute' above to run the intelligence pipeline.</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default PresentationMode;
