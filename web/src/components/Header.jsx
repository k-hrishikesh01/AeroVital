import React, { useState, useRef, useEffect } from 'react';
import useAuth from '../hooks/useAuth';
import BrandLogo from './common/BrandLogo';

export function Header({
  liveStatus,
  mission,
  alertCount = 0,
  onOpenAlerts,
  onOpenProfile,
  theme = 'dark',
  onToggleTheme,
  isMobilePreview,
  onToggleMobilePreview,
  currentView = 'cockpit',
  onSelectView,
}) {
  const { user, pilot, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showThemeMenu, setShowThemeMenu] = useState(false);
  const [showMobileNav, setShowMobileNav] = useState(false);

  const userMenuRef = useRef(null);
  const themeMenuRef = useRef(null);

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setShowUserMenu(false);
      }
      if (themeMenuRef.current && !themeMenuRef.current.contains(e.target)) {
        setShowThemeMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getStatusBadge = () => {
    switch (liveStatus) {
      case 'LIVE':
        return (
          <span className="live-badge" title="Telemetry stream active and synchronized">
            <span className="pulse-dot"></span>
            <span>Live Telemetry</span>
          </span>
        );
      case 'RESEARCH_MODE':
        return (
          <span
            className="live-badge research-badge"
            style={{
              backgroundColor: 'var(--brand-saffron-tint)',
              color: 'var(--brand-saffron)',
              borderColor: 'var(--brand-saffron)',
            }}
            title="Synthetic Research Lab mode"
          >
            <span className="pulse-dot" style={{ backgroundColor: 'var(--brand-saffron)' }}></span>
            <span>Research Mode</span>
          </span>
        );
      case 'STALE':
        return (
          <span className="live-badge stale" title="Telemetry stream delayed">
            <span className="pulse-dot"></span>
            <span>Stale Data</span>
          </span>
        );
      case 'INSUFFICIENT_DATA':
        return <span className="live-badge insufficient">Insufficient Data</span>;
      case 'BACKEND_UNAVAILABLE':
        return <span className="live-badge unavailable">Backend Offline</span>;
      case 'NO_TELEMETRY':
        return <span className="live-badge insufficient">No Telemetry</span>;
      default:
        return <span className="live-badge">Connecting...</span>;
    }
  };

  const pilotName = pilot?.name || user?.username || 'Pilot';
  const pilotCode = pilot?.pilot_code || (user ? `ID #${user.user_id}` : 'Crew');
  const avatarInitials =
    pilotName
      .replace(/^(Capt\.|F\/O|Captain)\s+/i, '')
      .trim()
      .split(' ')
      .map((p) => p[0])
      .join('')
      .substring(0, 2)
      .toUpperCase() || 'PL';

  return (
    <header className="aerovital-header" role="banner">
      <div className="header-tricolour-stripe" />
      <div className="header-container">
        {/* Left: Brand + View Switcher */}
        <div className="header-left">
          <div className="brand-wrapper">
            <BrandLogo variant="auto" size={32} showText={true} />
            <span className="brand-version-pill desktop-only">v1.2</span>
          </div>

          <div className="desktop-only">{getStatusBadge()}</div>

          {onSelectView && (
            <nav className="view-mode-switcher desktop-only" aria-label="Workbench View Switcher">
              <button
                type="button"
                className={`mode-btn ${currentView === 'cockpit' ? 'active' : ''}`}
                onClick={() => onSelectView('cockpit')}
                title="Switch to Operational Cockpit"
              >
                Operational Cockpit
              </button>
              <button
                type="button"
                className={`mode-btn ${currentView === 'research' ? 'active' : ''}`}
                onClick={() => onSelectView('research')}
                title="Switch to Research Lab Workbench"
              >
                Research Lab
              </button>
            </nav>
          )}
        </div>

        {/* Center: Mission Context Info */}
        <div className="header-center-info desktop-only">
          {mission ? (
            <div className="flight-tag" title="Active Mission Flight Context">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.3c.4-.2.6-.6.5-1.1z" />
              </svg>
              <span>
                Mission <strong>{mission.code || mission.mission_code}</strong>
              </span>
              <span className="tag-separator">|</span>
              <span>
                Phase: <strong>{mission.phase || mission.current_phase || 'Active'}</strong>
              </span>
              <span className="tag-separator">|</span>
              <span>
                G-Load: <strong>{mission.g_load !== undefined && mission.g_load !== null ? `${mission.g_load} G` : '1.0 G'}</strong>
              </span>
            </div>
          ) : (
            <div className="flight-tag inactive" style={{ opacity: 0.85 }}>
              <span>No Active Flight Mission</span>
            </div>
          )}
        </div>

        {/* Right: Actions */}
        <div className="header-actions">
          {/* Mobile Preview Frame Toggle (Desktop) */}
          {onToggleMobilePreview && (
            <button
              type="button"
              className="btn-secondary desktop-only"
              onClick={onToggleMobilePreview}
              title={isMobilePreview ? 'Switch to Full Desktop View' : 'Simulate Mobile Device View'}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect>
                <line x1="12" y1="18" x2="12.01" y2="18"></line>
              </svg>
              <span>{isMobilePreview ? 'Desktop View' : 'Mobile View'}</span>
            </button>
          )}

          {/* Theme Toggle Button (Maintains exact attributes for existing test suite) */}
          <button
            type="button"
            className="btn-icon theme-btn"
            onClick={onToggleTheme}
            title={theme === 'dark' ? 'Switch to Standard Light Mode' : 'Switch to Cockpit Night HUD Mode'}
            aria-label="Toggle Cockpit Theme"
          >
            {theme === 'dark' ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="5"></circle>
                <line x1="12" y1="1" x2="12" y2="3"></line>
                <line x1="12" y1="21" x2="12" y2="23"></line>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                <line x1="1" y1="12" x2="3" y2="12"></line>
                <line x1="21" y1="12" x2="23" y2="12"></line>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
              </svg>
            )}
          </button>

          {/* Notifications Bell */}
          <button
            type="button"
            className="btn-icon alerts-bell-btn"
            onClick={onOpenAlerts}
            title="View Flight Safety Alerts"
            aria-label="Flight Alerts"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            </svg>
            {alertCount > 0 && <span className="badge-counter">{alertCount}</span>}
          </button>

          {/* Pilot Profile Button & Dropdown */}
          <div style={{ position: 'relative' }} ref={userMenuRef}>
            <button
              type="button"
              className="pilot-profile-btn"
              onClick={() => setShowUserMenu((prev) => !prev)}
              title="Pilot Account Details"
              aria-expanded={showUserMenu}
              aria-haspopup="true"
            >
              <div className="pilot-avatar-badge">{avatarInitials}</div>
              <div className="pilot-header-meta desktop-only">
                <span className="pilot-header-name">{pilotName}</span>
                <span className="pilot-header-role">{pilotCode}</span>
              </div>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="desktop-only">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </button>

            {showUserMenu && (
              <div
                className="header-dropdown-menu"
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '100%',
                  marginTop: '8px',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-light)',
                  borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-lg)',
                  width: '220px',
                  padding: '6px',
                  zIndex: 200,
                }}
              >
                <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
                  <div style={{ fontWeight: 700, fontSize: '13px', color: 'var(--text-primary)' }}>{pilotName}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{user?.email || pilotCode}</div>
                </div>

                <button
                  type="button"
                  className="dropdown-item-btn"
                  onClick={() => {
                    setShowUserMenu(false);
                    if (onOpenProfile) onOpenProfile();
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                  </svg>
                  <span>Pilot Profile</span>
                </button>

                {onSelectView && (
                  <button
                    type="button"
                    className="dropdown-item-btn mobile-view-toggle-btn"
                    style={{
                      color: currentView === 'cockpit' ? 'var(--brand-saffron)' : 'var(--brand-green)',
                      fontWeight: 600,
                    }}
                    onClick={() => {
                      setShowUserMenu(false);
                      onSelectView(currentView === 'cockpit' ? 'research' : 'cockpit');
                    }}
                  >
                    <span style={{ fontSize: '14px' }}>{currentView === 'cockpit' ? '🔬' : '✈️'}</span>
                    <span>{currentView === 'cockpit' ? 'Switch to Research Lab' : 'Switch to Cockpit'}</span>
                  </button>
                )}

                <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '4px 0' }} />

                <button
                  type="button"
                  className="dropdown-item-btn"
                  style={{ color: 'var(--color-alert)' }}
                  onClick={() => {
                    setShowUserMenu(false);
                    logout();
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                    <polyline points="16 17 21 12 16 7"></polyline>
                    <line x1="21" y1="12" x2="9" y2="12"></line>
                  </svg>
                  <span>Log Out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
