import React, { useState } from 'react';

export function EngineExecutionBar({
  selectedSessionId,
  isExecuting,
  onExecute,
  latestRun,
  onOpenExport,
  onOpenComparison,
  onOpenRunsHistory,
  onOpenPresentation,
}) {
  const [runNotes, setRunNotes] = useState('');

  const handleExecuteClick = () => {
    if (!selectedSessionId || isExecuting) return;
    onExecute(selectedSessionId, runNotes);
  };

  return (
    <div className="research-card execution-bar-card">
      <div className="execution-controls-left">
        <div className="engine-badge-cluster">
          <span className="engine-tag">AeroVital Engine v1.0.0</span>
          <span className="pipeline-tag">AeroVitalPipeline</span>
          <span className="estimator-tag">ProvisionalRuleBasedEstimator</span>
        </div>

        <div className="execution-notes-input-wrapper">
          <input
            type="text"
            className="research-notes-input"
            placeholder="Add optional notes for this execution run..."
            value={runNotes}
            onChange={(e) => setRunNotes(e.target.value)}
            disabled={isExecuting || !selectedSessionId}
          />
        </div>
      </div>

      <div className="execution-controls-right">
        {latestRun && (
          <div className="execution-throughput-meta">
            <span className="throughput-val">{latestRun.throughput_samples_per_sec || '—'} samples/s</span>
            <span className="throughput-lbl">({latestRun.execution_duration_sec}s runtime)</span>
          </div>
        )}

        {/* Presentation Mode Toggle */}
        <button
          className="btn-secondary presentation-mode-btn"
          onClick={onOpenPresentation}
          title="Launch Fullscreen 5-Scenario Research Demonstration Mode"
          style={{
            borderColor: 'var(--brand-saffron)',
            color: 'var(--brand-saffron)',
            fontWeight: 700,
          }}
        >
          <span>📊 Presentation Mode</span>
        </button>

        {/* Consolidated Run History & Compare Runs */}
        <button
          className="btn-secondary"
          onClick={onOpenComparison}
          title="View Historical Research Runs and Side-by-Side Comparisons"
        >
          Run History & Comparison
        </button>

        {/* Export Data */}
        <button
          className="btn-secondary"
          onClick={onOpenExport}
          disabled={!selectedSessionId}
          title="Export Session Observations and Evaluation"
        >
          Export Data
        </button>

        {/* Primary Execute Button */}
        <button
          className="btn-primary execute-btn"
          onClick={handleExecuteClick}
          disabled={isExecuting || !selectedSessionId}
        >
          {isExecuting ? (
            <>
              <div className="spinner-subtle inline" />
              <span>Evaluating Pipeline...</span>
            </>
          ) : (
            <>
              <span>Execute Pipeline</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

export default EngineExecutionBar;
