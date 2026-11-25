import React from 'react';
import useAuth from '../hooks/useAuth';
import BrandLogo from './common/BrandLogo';

export function PilotProfileModal({ isOpen, onClose }) {
  const { user, pilot } = useAuth();
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop active" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        {/* Subtle Tricolour Accent Line */}
        <div
          style={{
            height: '2px',
            width: '100%',
            background: 'var(--brand-tricolour-bar)',
            borderRadius: '2px 2px 0 0',
            marginBottom: '16px',
          }}
        />

        <button className="modal-close-btn" onClick={onClose} aria-label="Close dialog" style={{ position: 'absolute', top: '16px', right: '16px' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '16px' }}>
          <BrandLogo variant="auto" size={42} />
          <div>
            <h2 className="modal-header-title" style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Pilot Flight Clearance Dossier
            </h2>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              AeroVital Personnel Telemetry Identity
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-card-tinted)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Account Username:</span>
            <strong>{user?.username || 'N/A'}</strong>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-card-tinted)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Pilot Code:</span>
            <strong style={{ color: 'var(--brand-saffron)' }}>{pilot?.pilot_code || 'Unassigned'}</strong>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-card-tinted)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Pilot Full Name:</span>
            <strong>{pilot?.name || user?.username}</strong>
          </div>

          {pilot?.age && (
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-card-tinted)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Age / Sex:</span>
              <strong>{pilot.age} yrs • {pilot.sex || 'N/A'}</strong>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-card-tinted)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Backend Pilot ID:</span>
            <span style={{ fontFamily: 'monospace', fontSize: '11px', color: 'var(--text-muted)' }}>{pilot?.id || 'N/A'}</span>
          </div>
        </div>

        <button
          className="btn-create-account"
          onClick={onClose}
          style={{ marginTop: '20px' }}
        >
          Close Profile
        </button>
      </div>
    </div>
  );
}

export default PilotProfileModal;
