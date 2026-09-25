import React from 'react';
import { formatScore, formatPercentage, formatTime, getFatigueStateConfig } from '../utils/formatters';

export function CurrentStateCard({ currentState }) {
  const stateConfig = getFatigueStateConfig(currentState?.current_state);
  const fatigueScore = currentState?.fatigue_score;
  const confidence = currentState?.confidence;
  const overallSqi = currentState?.overall_sqi;
  const dominantFactors = currentState?.dominant_factors || [];

  return (
    <>
      {/* Dual Score Row: Fatigue Score & Sensor Confidence */}
      <div className="dual-score-row">
        <article className="score-card" aria-label="Fatigue Score">
          <span className="card-label">Fatigue Score</span>
          <div className="score-value mono-num">
            {fatigueScore !== null && fatigueScore !== undefined ? formatScore(fatigueScore) : 'N/A'}
          </div>
          <div className="score-trend" style={{ color: stateConfig.color }}>
            <span>Core Latent Index</span>
          </div>
        </article>

        <article className="score-card" aria-label="Estimation Confidence">
          <span className="card-label">Confidence</span>
          <div className="score-value mono-num">
            {confidence !== null && confidence !== undefined ? formatPercentage(confidence) : '0%'}
          </div>
          <div className="score-trend" style={{ color: 'var(--text-secondary)' }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
            <span>SQI: {formatPercentage(overallSqi)}</span>
          </div>
        </article>
      </div>

      {/* Primary Condition State Card */}
      <article className={`condition-card ${stateConfig.variant}`} aria-label="Current Fatigue Classification">
        <div className="condition-value-row">
          <span className="card-label">AeroVital Condition</span>
          <span
            className="condition-pill"
            style={{ backgroundColor: stateConfig.bgColor, color: stateConfig.color }}
          >
            {currentState?.current_state === 'INSUFFICIENT_DATA' ? 'Engine Abstained' : stateConfig.label}
          </span>
        </div>

        <div className="condition-badge-title" style={{ color: stateConfig.color }}>
          {stateConfig.label}
        </div>

        <div className="condition-subtext">
          {currentState?.timestamp
            ? `Estimated at ${formatTime(currentState.timestamp)} (Engine v${currentState.baseline_version || '1.0'})`
            : stateConfig.sublabel}
        </div>

        {/* Dominant Factors list from AeroVital Core */}
        {dominantFactors.length > 0 && (
          <div className="dominant-factors-box">
            <div className="dominant-factors-title">Contributing Factors (Core Engine):</div>
            <div>
              {dominantFactors.map((factor, idx) => (
                <span key={idx} className="factor-tag">
                  {factor}
                </span>
              ))}
            </div>
          </div>
        )}
      </article>
    </>
  );
}

export default CurrentStateCard;
