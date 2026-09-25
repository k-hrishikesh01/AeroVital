import React from 'react';

export function AtmosphericStrip({ mission, latestTelemetry, signalQuality }) {
  const gLoad = mission?.external_g_load !== null && mission?.external_g_load !== undefined
    ? `${mission.external_g_load.toFixed(2)} G`
    : (latestTelemetry?.accel_z ? `${latestTelemetry.accel_z.toFixed(2)} G` : '1.00 G');

  const skinTemp = latestTelemetry?.skin_temperature !== null && latestTelemetry?.skin_temperature !== undefined
    ? `${latestTelemetry.skin_temperature.toFixed(1)} °C`
    : 'N/A';

  const battery = latestTelemetry?.battery_level !== null && latestTelemetry?.battery_level !== undefined
    ? `${latestTelemetry.battery_level}%`
    : 'N/A';

  const motionIndex = signalQuality?.motion_corruption_index !== null && signalQuality?.motion_corruption_index !== undefined
    ? `${(signalQuality.motion_corruption_index * 100).toFixed(0)}%`
    : 'N/A';

  return (
    <div className="telemetry-strip" aria-label="Flight Environmental & Motion Strip">
      <div className="strip-card">
        <div className="strip-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
          </svg>
        </div>
        <div className="strip-content">
          <span className="strip-label">External G-Load</span>
          <span className="strip-value mono-num">{gLoad}</span>
        </div>
      </div>

      <div className="strip-card">
        <div className="strip-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"></path>
          </svg>
        </div>
        <div className="strip-content">
          <span className="strip-label">Skin Temperature</span>
          <span className="strip-value mono-num">{skinTemp}</span>
        </div>
      </div>

      <div className="strip-card">
        <div className="strip-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="1" y="6" width="18" height="12" rx="2" ry="2"></rect>
            <line x1="23" y1="13" x2="23" y2="11"></line>
          </svg>
        </div>
        <div className="strip-content">
          <span className="strip-label">Sensor Battery</span>
          <span className="strip-value mono-num">{battery}</span>
        </div>
      </div>

      <div className="strip-card">
        <div className="strip-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
        </div>
        <div className="strip-content">
          <span className="strip-label">Motion Corruption</span>
          <span className="strip-value mono-num">{motionIndex}</span>
        </div>
      </div>
    </div>
  );
}

export default AtmosphericStrip;
