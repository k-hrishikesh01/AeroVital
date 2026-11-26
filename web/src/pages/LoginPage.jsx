import React, { useState } from 'react';
import useAuth from '../hooks/useAuth';
import BrandLogo from '../components/common/BrandLogo';

export function LoginPage() {
  const { login, isLoading, authError } = useAuth();
  const [username, setUsername] = useState('demo_researcher');
  const [password, setPassword] = useState('AeroVital2026!');
  const [localError, setLocalError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError(null);

    if (!username.trim() || !password) {
      setLocalError('Please enter both username and password.');
      return;
    }

    try {
      await login(username.trim(), password);
    } catch (err) {
      setLocalError(err.message || 'Authentication failed. Please verify credentials.');
    }
  };

  return (
    <div className="login-wrapper">
      <div className="login-card">
        {/* Subtle Tricolour Accent Line at the top of the card */}
        <div
          className="card-tricolour-accent"
          style={{
            height: '3px',
            width: '100%',
            background: 'var(--brand-tricolour-bar)',
            borderRadius: '2px 2px 0 0',
            marginBottom: '28px',
          }}
        />

        {/* Official AeroVital Emblem & Aviation Brand Lockup */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '28px' }}>
          <BrandLogo variant="auto" size={76} alt="AeroVital Official Aircraft Emblem" />
          <h1
            className="brand-title"
            style={{
              fontSize: '24px',
              fontWeight: 800,
              letterSpacing: '0.08em',
              marginTop: '14px',
              textTransform: 'uppercase',
            }}
          >
            AEROVITAL
          </h1>
          <span
            style={{
              fontSize: '12px',
              fontWeight: 600,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              color: 'var(--text-secondary)',
              marginTop: '4px',
            }}
          >
            Flight Deck Biometrics & Fatigue Intelligence
          </span>
        </div>

        <h2 className="login-header-title" style={{ fontSize: '18px', fontWeight: 700, marginBottom: '20px' }}>
          Pilot Authentication
        </h2>

        {(localError || authError) && (
          <div className="auth-error-banner" role="alert">
            {localError || authError}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="username">Username / Pilot ID</label>
            <input
              id="username"
              type="text"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. pilot_01 or admin"
              autoComplete="username"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            className="btn-create-account"
            disabled={isLoading}
          >
            {isLoading ? 'Authenticating...' : 'Sign In to Dashboard'}
          </button>
        </form>

        <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
          AeroVital Mission-Critical Aeromedical System. Authorized flight personnel only.
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
