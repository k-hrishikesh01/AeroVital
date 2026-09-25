import React from 'react';
import { formatRelativeTime } from '../utils/formatters';

export function AlertsDrawer({ isOpen, onClose, alerts = [], onAcknowledge }) {
  return (
    <div className={`drawer-backdrop ${isOpen ? 'active' : ''}`} onClick={onClose}>
      <div className="drawer-panel" onClick={e => e.stopPropagation()}>
        <div className="drawer-header">
          <h3 className="drawer-title">Flight Safety Alerts</h3>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close alerts drawer">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {alerts.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 12px' }}>
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              <div>All flight parameters optimal. No active safety alerts.</div>
            </div>
          ) : (
            alerts.map(alert => {
              const severityClass = alert.severity === 'CRITICAL'
                ? 'alert-critical'
                : (alert.severity === 'WARNING' ? 'alert-warning' : '');

              return (
                <div key={alert.id} className={`alert-card-item ${severityClass}`}>
                  <div className="alert-top">
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontWeight: 800,
                        backgroundColor: alert.severity === 'CRITICAL' ? 'var(--color-alert)' : (alert.severity === 'WARNING' ? 'var(--color-warning)' : 'var(--color-cyan)'),
                        color: '#fff',
                      }}>
                        {alert.severity}
                      </span>
                      {alert.alert_type}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {formatRelativeTime(alert.timestamp)}
                    </span>
                  </div>

                  <div className="alert-desc">{alert.message}</div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      Trigger: <strong>{alert.trigger_state || 'Telemetry Threshold'}</strong>
                    </span>

                    <button
                      className="btn-ack"
                      onClick={() => onAcknowledge(alert.id)}
                      title="Acknowledge alert on backend"
                    >
                      Acknowledge
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export default AlertsDrawer;
