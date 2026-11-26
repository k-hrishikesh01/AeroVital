import React, { useState, useRef, useEffect } from 'react';
import { useTheme } from '../../context/ThemeContext';

export function AppearanceSelector({ compact = false }) {
  const { themePreference, resolvedTheme, systemIsDark, setThemePreference, toggleTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getActiveIcon = () => {
    if (resolvedTheme === 'dark') {
      return (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      );
    }
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
      </svg>
    );
  };

  const getSystemLabel = () => `System (${systemIsDark ? 'Dark' : 'Light'})`;

  return (
    <div className="appearance-selector-wrapper" ref={containerRef} style={{ position: 'relative' }}>
      <button
        type="button"
        className="btn-icon theme-toggle-btn"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label="Toggle Cockpit Theme"
        aria-expanded={isOpen}
        aria-haspopup="true"
        title={
          themePreference === 'system'
            ? `Appearance: ${getSystemLabel()}`
            : themePreference === 'dark'
            ? 'Appearance: Dark (Aviation Command HUD)'
            : 'Appearance: Light (Daylight Clinical)'
        }
      >
        {getActiveIcon()}
        {themePreference === 'system' && (
          <span className="system-dot-indicator" title="Syncing with OS theme" />
        )}
      </button>

      {isOpen && (
        <div
          className="appearance-dropdown-menu"
          role="menu"
          aria-label="Theme options"
          style={{
            position: 'absolute',
            right: 0,
            top: 'calc(100% + 8px)',
            minWidth: '220px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-lg)',
            padding: '6px',
            zIndex: 300,
          }}
        >
          <div
            style={{
              padding: '6px 10px 4px 10px',
              fontSize: '11px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-muted)',
              borderBottom: '1px solid var(--border-subtle)',
              marginBottom: '4px',
            }}
          >
            Interface Appearance
          </div>

          <button
            type="button"
            className={`appearance-option-btn ${themePreference === 'system' ? 'active' : ''}`}
            onClick={() => {
              setThemePreference('system');
              setIsOpen(false);
            }}
            role="menuitem"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
              <span>{getSystemLabel()}</span>
            </div>
            {themePreference === 'system' && <span className="check-mark">✓</span>}
          </button>

          <button
            type="button"
            className={`appearance-option-btn ${themePreference === 'light' ? 'active' : ''}`}
            onClick={() => {
              setThemePreference('light');
              setIsOpen(false);
            }}
            role="menuitem"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
              <span>Light Mode</span>
            </div>
            {themePreference === 'light' && <span className="check-mark">✓</span>}
          </button>

          <button
            type="button"
            className={`appearance-option-btn ${themePreference === 'dark' ? 'active' : ''}`}
            onClick={() => {
              setThemePreference('dark');
              setIsOpen(false);
            }}
            role="menuitem"
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
              <span>Dark Mode (Aviation Navy)</span>
            </div>
            {themePreference === 'dark' && <span className="check-mark">✓</span>}
          </button>
        </div>
      )}
    </div>
  );
}

export default AppearanceSelector;
