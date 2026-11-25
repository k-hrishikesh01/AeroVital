import React from 'react';

export function ECGStatusPanel() {
  return (
    <article className="chart-card" aria-label="ECG Channel Status">
      <div className="chart-header" style={{ marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{
            fontSize: '11px',
            fontWeight: 800,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            padding: '3px 8px',
            borderRadius: '4px',
            backgroundColor: 'var(--bg-card-tinted)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-light)'
          }}>
            ECG
          </span>
          <h3 className="chart-title" style={{ margin: 0, fontSize: '14px' }}>Lead-II Electrocardiogram</h3>
        </div>

        <span style={{
          fontSize: '11px',
          fontWeight: 800,
          textTransform: 'uppercase',
          padding: '3px 10px',
          borderRadius: '12px',
          backgroundColor: 'rgba(148, 163, 184, 0.15)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border-light)'
        }}>
          UNAVAILABLE
        </span>
      </div>

      <div style={{
        padding: '16px 20px',
        backgroundColor: 'var(--bg-card-tinted)',
        borderRadius: '12px',
        border: '1px dashed var(--border-light)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}>
        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
          Current acquisition path does not provide ECG.
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          Galaxy Watch PPG sensor provides optical heart rate and motion telemetry. Lead-II hardware stream ingestion is unattached.
        </div>
      </div>
    </article>
  );
}

export default ECGStatusPanel;
