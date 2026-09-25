import React from 'react';
import { formatPercentage } from '../utils/formatters';

export function TelemetryDetails({ latestTelemetry, recentFeatures, signalQuality }) {
  const heartRate = latestTelemetry?.heart_rate !== null && latestTelemetry?.heart_rate !== undefined
    ? `${Math.round(latestTelemetry.heart_rate)} BPM`
    : 'N/A';

  const spo2 = latestTelemetry?.spo2 !== null && latestTelemetry?.spo2 !== undefined
    ? `${latestTelemetry.spo2.toFixed(1)}%`
    : 'N/A';

  const skinTemp = latestTelemetry?.skin_temperature !== null && latestTelemetry?.skin_temperature !== undefined
    ? `${latestTelemetry.skin_temperature.toFixed(1)} °C`
    : 'N/A';

  const rmssd = recentFeatures?.rmssd_ms !== null && recentFeatures?.rmssd_ms !== undefined
    ? `${Math.round(recentFeatures.rmssd_ms)} ms`
    : (latestTelemetry?.rr_interval ? `${Math.round(latestTelemetry.rr_interval)} ms (RR)` : 'N/A');

  const activity = latestTelemetry?.activity_level || 'Stationary';

  const sqiAcceptable = signalQuality?.is_telemetry_acceptable;
  const sqiStatus = sqiAcceptable === undefined || sqiAcceptable === null
    ? 'N/A'
    : (sqiAcceptable ? 'Acceptable' : 'Noise Corrupted');

  return (
    <section className="details-container" aria-label="Physiological Telemetry Channels">
      <h2 className="details-title">Physiological Details (Telemetry)</h2>

      <div className="details-list">
        {/* Heart Rate */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-alert)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
              </svg>
            </div>
            <span className="detail-label">Heart Rate</span>
          </div>
          <span className="detail-value mono-num">{heartRate}</span>
        </div>

        {/* Blood Oxygen SpO2 */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-cyan)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path>
              </svg>
            </div>
            <span className="detail-label">Oxygen Saturation (SpO2)</span>
          </div>
          <span className="detail-value mono-num">{spo2}</span>
        </div>

        {/* HRV RMSSD */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-purple)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
            </div>
            <span className="detail-label">HRV (RMSSD / RR)</span>
          </div>
          <span className="detail-value mono-num">{rmssd}</span>
        </div>

        {/* Skin Temperature */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-warning)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path>
              </svg>
            </div>
            <span className="detail-label">Skin Temperature</span>
          </div>
          <span className="detail-value mono-num">{skinTemp}</span>
        </div>

        {/* Activity State */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-normal)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 6v6l4 2"></path>
              </svg>
            </div>
            <span className="detail-label">Activity Context</span>
          </div>
          <span className="detail-value">{activity}</span>
        </div>

        {/* Signal Quality Status */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--primary-navy)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M2 12h20M12 2v20"></path>
              </svg>
            </div>
            <span className="detail-label">Sensor Telemetry Fidelity</span>
          </div>
          <span className="detail-value" style={{ color: sqiAcceptable === false ? 'var(--color-alert)' : 'inherit' }}>
            {sqiStatus}
          </span>
        </div>
      </div>
    </section>
  );
}

export default TelemetryDetails;
