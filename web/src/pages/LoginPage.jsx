import React, { useState } from 'react';
import useAuth from '../hooks/useAuth';

export function LoginPage() {
  const { login, isLoading, authError } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
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
        {/* Logo and Brand */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'var(--primary-navy-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary-navy)', marginBottom: '12px' }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
              <path d="M2 17l10 5 10-5"></path>
              <path d="M2 12l10 5 10-5"></path>
            </svg>
          </div>
          <h1 className="brand-title" style={{ fontSize: '22px' }}>AEROVITAL</h1>
          <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Flight Deck Biometrics & Fatigue Intelligence</span>
        </div>

        <h2 className="login-header-title">Pilot Authentication</h2>

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

        <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
          AeroVital Mission-Critical Aeromedical System. Authorized flight personnel only.
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
