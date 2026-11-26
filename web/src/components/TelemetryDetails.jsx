import React from 'react';
import { formatPercentage } from '../utils/formatters';

export function TelemetryDetails({ latestTelemetry, recentFeatures, signalQuality, latestHeartRate }) {
  const hrVal = (latestHeartRate !== null && latestHeartRate !== undefined)
    ? latestHeartRate
    : (latestTelemetry?.heart_rate !== null && latestTelemetry?.heart_rate !== undefined ? latestTelemetry.heart_rate : null);

  const heartRate = hrVal !== null
    ? `${Math.round(hrVal)} BPM`
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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div>
          <h2 className="details-title" style={{ margin: 0 }}>Physiological Details (Telemetry)</h2>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Raw Ingested Sensor Observations</span>
        </div>
        <span style={{ fontSize: '10px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
          1 Hz Optical Stream
        </span>
      </div>

      <div className="details-list">
        {/* Heart Rate */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-alert)' }} aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
              </svg>
            </div>
            <div>
              <span className="detail-label">Heart Rate</span>
              <span className="detail-channel-subtext">Galaxy Watch PPG</span>
            </div>
          </div>
          <span className="detail-value mono-num">{heartRate}</span>
        </div>

        {/* Blood Oxygen SpO2 */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-cyan)' }} aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path>
              </svg>
            </div>
            <div>
              <span className="detail-label">Oxygen Saturation (SpO2)</span>
              <span className="detail-channel-subtext">Uninstrumented</span>
            </div>
          </div>
          <span className="detail-value mono-num">{spo2}</span>
        </div>

        {/* HRV RMSSD */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-purple)' }} aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
              </svg>
            </div>
            <div>
              <span className="detail-label">HRV (RMSSD / RR)</span>
              <span className="detail-channel-subtext">IBI Inter-Beat Variance</span>
            </div>
          </div>
          <span className="detail-value mono-num">{rmssd}</span>
        </div>

        {/* Skin Temperature */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-warning)' }} aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path>
              </svg>
            </div>
            <div>
              <span className="detail-label">Skin Temperature</span>
              <span className="detail-channel-subtext">Uninstrumented</span>
            </div>
          </div>
          <span className="detail-value mono-num">{skinTemp}</span>
        </div>

        {/* Activity State */}
        <div className="detail-item">
          <div className="detail-left">
            <div className="detail-icon" style={{ color: 'var(--color-normal)' }} aria-hidden="true">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 6v6l4 2"></path>
              </svg>
            </div>
            <div>
              <span className="detail-label">Activity Context</span>
              <span className="detail-channel-subtext">Motion Accelerometer</span>
            </div>
          </div>
          <span className="detail-value">{activity}</span>
        </div>
      </div>
    </section>
  );
}

export default TelemetryDetails;
