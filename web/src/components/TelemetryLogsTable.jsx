import React from 'react';
import { formatTime } from '../utils/formatters';

export function TelemetryLogsTable({ telemetry = [], flightCode = 'AV-409' }) {
  const exportCSV = () => {
    if (!telemetry || telemetry.length === 0) return;
    const headers = ['Timestamp', 'HeartRate_BPM', 'SpO2_Percent', 'RR_Interval_ms', 'SkinTemp_C', 'Activity'];
    const rows = telemetry.map(t => [
      t.timestamp,
      t.heart_rate !== null ? t.heart_rate : '',
      t.spo2 !== null ? t.spo2 : '',
      t.rr_interval !== null ? t.rr_interval : '',
      t.skin_temperature !== null ? t.skin_temperature : '',
      `"${t.activity_level || ''}"`,
    ].join(','));

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `AeroVital_Telemetry_${flightCode}_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <article className="logs-section" aria-label="Ingested Telemetry Log History">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h3 className="chart-title">Flight Telemetry Packet History</h3>
          <span className="chart-subtitle">
            Recent physiological samples verified by backend (/api/v1/telemetry/)
          </span>
        </div>

        <button
          className="btn-secondary"
          onClick={exportCSV}
          disabled={telemetry.length === 0}
          title="Download actual telemetry records as CSV"
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          <span>Export CSV</span>
        </button>
      </div>

      <div className="table-responsive">
        {telemetry.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            No telemetry records available in session history.
          </div>
        ) : (
          <table className="telemetry-table">
            <thead>
              <tr>
                <th>Sample Time</th>
                <th>Heart Rate</th>
                <th>SpO2</th>
                <th>RR Interval</th>
                <th>Skin Temp</th>
                <th>Activity</th>
              </tr>
            </thead>
            <tbody>
              {telemetry.slice(0, 15).map((log, idx) => (
                <tr key={log.id || idx}>
                  <td style={{ fontWeight: 600 }} className="mono-num">{formatTime(log.timestamp)}</td>
                  <td>
                    <strong style={{ color: 'var(--primary-navy)' }}>
                      {log.heart_rate !== null ? `${Math.round(log.heart_rate)} BPM` : 'N/A'}
                    </strong>
                  </td>
                  <td>
                    <span style={{ fontWeight: 700, color: 'var(--color-cyan)' }}>
                      {log.spo2 !== null ? `${log.spo2.toFixed(1)}%` : 'N/A'}
                    </span>
                  </td>
                  <td className="mono-num">{log.rr_interval !== null ? `${Math.round(log.rr_interval)} ms` : 'N/A'}</td>
                  <td className="mono-num">{log.skin_temperature !== null ? `${log.skin_temperature.toFixed(1)} °C` : 'N/A'}</td>
                  <td>{log.activity_level || 'Stationary'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </article>
  );
}

export default TelemetryLogsTable;
