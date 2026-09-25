import React from 'react';
import { formatFreshness } from '../utils/formatters';

export function StatusBanner({
  liveStatus,
  freshnessSec,
  isRefreshing,
  onRefresh,
  disclaimer,
  errorMessage,
}) {
  return (
    <section className="control-banner" aria-label="System Connectivity & Engine Status">
      <div className="banner-left">
        <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-secondary)' }}>
          System Telemetry Status:
        </span>

        {liveStatus === 'LIVE' && (
          <span className="live-badge" title="Telemetry stream active and synchronized with flight deck">
            <span className="pulse-dot"></span> Live Telemetry ({formatFreshness(freshnessSec)})
          </span>
        )}

        {liveStatus === 'STALE' && (
          <span className="live-badge stale" title="Telemetry stream delay detected">
            <span className="pulse-dot"></span> Telemetry Stale ({formatFreshness(freshnessSec)})
          </span>
        )}

        {liveStatus === 'INSUFFICIENT_DATA' && (
          <span className="live-badge insufficient" title="Intelligence engine abstaining due to low SQI or missing baselines">
            ⚠️ INSUFFICIENT DATA (AeroVital Engine Abstaining)
          </span>
        )}

        {liveStatus === 'NO_TELEMETRY' && (
          <span className="live-badge insufficient" title="No telemetry packets received for this session yet">
            Awaiting Telemetry Packets
          </span>
        )}

        {liveStatus === 'BACKEND_UNAVAILABLE' && (
          <span className="live-badge unavailable" title="Cannot connect to AeroVital Django backend">
            ⚠️ BACKEND OFFLINE (Check Django server at :8000)
          </span>
        )}

        {errorMessage && (
          <span style={{ fontSize: '12px', color: 'var(--color-alert)', fontWeight: 600 }}>
            {errorMessage}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {disclaimer && (
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            {disclaimer}
          </span>
        )}

        <button
          className="btn-secondary"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Manually sync telemetry and intelligence estimates"
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            style={{ animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }}
          >
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
          </svg>
          <span>{isRefreshing ? 'Syncing...' : 'Sync'}</span>
        </button>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </section>
  );
}

export default StatusBanner;
