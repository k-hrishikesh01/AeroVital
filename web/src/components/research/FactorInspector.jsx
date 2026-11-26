import React from 'react';

export function FactorInspector({
  selectedWindow,
  runSummary,
}) {
  const factors = selectedWindow?.dominant_factors || runSummary?.dominant_factors_summary?.map(f => f.factor) || [];

  return (
    <div className="research-card factor-inspector-card">
      <div className="card-header-clean">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="research-badge-accent">RATIONALE AUDIT</span>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>
            {selectedWindow ? 'Window Explanatory Factors' : 'Session Dominant Factors'}
          </h3>
        </div>
        {selectedWindow && (
          <span className={`scenario-tag-badge ${selectedWindow.state?.toLowerCase()}`}>
            {selectedWindow.state}
          </span>
        )}
      </div>

      {selectedWindow ? (
        <div className="selected-window-meta-strip">
          <div className="meta-box">
            <span className="lbl">Timestamp</span>
            <span className="val">{selectedWindow.timestamp?.substring(11, 19)} UTC</span>
          </div>
          <div className="meta-box">
            <span className="lbl">Confidence Score</span>
            <span className="val">{selectedWindow.confidence}</span>
          </div>
          <div className="meta-box">
            <span className="lbl">Composite SQI</span>
            <span className="val">{selectedWindow.sqi}</span>
          </div>
        </div>
      ) : runSummary ? (
        <div className="selected-window-meta-strip">
          <div className="meta-box">
            <span className="lbl">Mean Confidence</span>
            <span className="val">{runSummary.mean_confidence || '—'}</span>
          </div>
          <div className="meta-box">
            <span className="lbl">Mean SQI</span>
            <span className="val">{runSummary.mean_sqi || '—'}</span>
          </div>
          <div className="meta-box">
            <span className="lbl">Abstention Rate</span>
            <span className="val">{runSummary.abstention_rate_pct}%</span>
          </div>
        </div>
      ) : null}

      <div className="factors-list-container">
        {factors.length === 0 ? (
          <div className="research-empty-state">
            <span>No specific factors recorded. Select an evaluated window along the timeline to inspect evidence predicates.</span>
          </div>
        ) : (
          factors.map((factorText, idx) => {
            const isAbstainReason = factorText.toLowerCase().includes('insufficient') || factorText.toLowerCase().includes('missing');
            const isWorkloadReason = factorText.toLowerCase().includes('workload') || factorText.toLowerCase().includes('g-load');
            const isNormalReason = factorText.toLowerCase().includes('normal') || factorText.toLowerCase().includes('concordance');

            let icon = '•';
            if (isAbstainReason) icon = '⚠️';
            else if (isWorkloadReason) icon = '⚡';
            else if (isNormalReason) icon = '✓';

            return (
              <div key={idx} className={`factor-item ${isAbstainReason ? 'abstain' : ''}`}>
                <span className="factor-icon">{icon}</span>
                <span className="factor-text">{factorText}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

export default FactorInspector;
