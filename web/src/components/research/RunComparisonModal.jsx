import React, { useState, useEffect } from 'react';
import researchApi from '../../services/researchApi';

export function RunComparisonModal({
  isOpen,
  onClose,
  initialRunIds = [],
}) {
  const [availableRuns, setAvailableRuns] = useState([]);
  const [selectedRunIds, setSelectedRunIds] = useState(initialRunIds);
  const [comparisonData, setComparisonData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadRunsList();
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedRunIds.length >= 2) {
      loadComparison();
    } else {
      setComparisonData(null);
    }
  }, [selectedRunIds]);

  const loadRunsList = async () => {
    try {
      const runs = await researchApi.getRuns({ limit: 50 });
      setAvailableRuns(runs || []);
      if (!selectedRunIds.length && runs && runs.length >= 2) {
        setSelectedRunIds([runs[0].run_id, runs[1].run_id]);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const loadComparison = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await researchApi.compareRuns(selectedRunIds);
      setComparisonData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleRunSelection = (runId) => {
    if (selectedRunIds.includes(runId)) {
      if (selectedRunIds.length > 2) {
        setSelectedRunIds(selectedRunIds.filter(id => id !== runId));
      }
    } else {
      if (selectedRunIds.length < 5) {
        setSelectedRunIds([...selectedRunIds, runId]);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop active comparison-modal-backdrop" onClick={onClose}>
      <div className="comparison-modal-container research-comparison-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header-research">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="research-badge-accent">RUN COMPARISON</span>
            <h3>Compare Research Pipeline Runs</h3>
          </div>
          <button type="button" className="btn-icon close-btn" onClick={onClose} aria-label="Close modal">&times;</button>
        </div>

        <div className="modal-body-research">
          {/* Run selection picker */}
          <div className="comparison-picker-bar">
            <span style={{ fontSize: '12px', fontWeight: 600 }}>Select Runs to Compare (2 to 4):</span>
            <div className="run-chips-container">
              {availableRuns.map(r => {
                const isSelected = selectedRunIds.includes(r.run_id);
                return (
                  <button
                    key={r.run_id}
                    className={`run-chip ${isSelected ? 'active' : ''}`}
                    onClick={() => toggleRunSelection(r.run_id)}
                  >
                    <span>{r.run_id}</span>
                    <span className="scen">({r.session_id} - {r.scenario?.replace(/_/g, ' ')})</span>
                  </button>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="research-error-banner">
              <span>{error}</span>
            </div>
          )}

          {isLoading ? (
            <div className="research-loading-state" style={{ minHeight: '200px' }}>
              <div className="spinner-subtle" />
              <span>Analyzing comparative metrics...</span>
            </div>
          ) : comparisonData ? (
            <div className="comparison-results-grid">
              {comparisonData.version_differences && (
                <div className="version-diff-callout">
                  <strong>Version Traceability:</strong>
                  {comparisonData.version_differences.engine_version_diff && (
                    <span className="diff-pill warning">Engine Version Divergence</span>
                  )}
                  {comparisonData.version_differences.dataset_version_diff && (
                    <span className="diff-pill warning">Dataset Version Divergence</span>
                  )}
                  {comparisonData.version_differences.scenario_diff && (
                    <span className="diff-pill info">Different Experimental Scenarios</span>
                  )}
                  {!comparisonData.version_differences.engine_version_diff && !comparisonData.version_differences.dataset_version_diff && !comparisonData.version_differences.scenario_diff && (
                    <span className="diff-pill match">Identical Engine & Dataset Baseline</span>
                  )}
                </div>
              )}

              <div className="runs-columns-container">
                {comparisonData.runs.map(run => (
                  <div key={run.run_id} className="comparison-column-card">
                    <div className="col-header">
                      <strong className="run-id-title">{run.run_id}</strong>
                      <span className="session-sub">{run.session_id} ({run.scenario})</span>
                    </div>

                    <div className="col-metrics-table">
                      <div className="row">
                        <span className="label">Engine Version:</span>
                        <span className="val">{run.engine_version}</span>
                      </div>
                      <div className="row">
                        <span className="label">Dataset Version:</span>
                        <span className="val">{run.dataset_version}</span>
                      </div>
                      <div className="row">
                        <span className="label">Throughput:</span>
                        <span className="val">{run.throughput_samples_per_sec} smp/s</span>
                      </div>
                      <div className="row">
                        <span className="label">Runtime:</span>
                        <span className="val">{run.execution_duration_sec}s</span>
                      </div>
                      <div className="row highlight">
                        <span className="label">Mean Confidence:</span>
                        <span className="val">{run.mean_confidence}</span>
                      </div>
                      <div className="row highlight">
                        <span className="label">Mean SQI:</span>
                        <span className="val">{run.mean_sqi}</span>
                      </div>
                      <div className="row highlight">
                        <span className="label">Abstention Rate:</span>
                        <span className="val">{run.abstention_rate_pct}%</span>
                      </div>
                    </div>

                    <div className="col-states-breakdown">
                      <span className="state-title">State Share:</span>
                      {Object.entries(run.state_breakdown || {}).map(([st, stat]) => (
                        <div key={st} className="state-bar-row">
                          <div className="st-info">
                            <span>{st}:</span>
                            <strong>{stat.percentage}%</strong>
                          </div>
                          <div className="bar-track">
                            <div className={`bar-fill ${st.toLowerCase()}`} style={{ width: `${stat.percentage}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="research-empty-state" style={{ minHeight: '160px' }}>
              <span>Select at least 2 runs above to render comparative breakdown.</span>
            </div>
          )}
        </div>

        <div className="modal-footer-research">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default RunComparisonModal;
