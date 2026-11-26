import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';

const ThemeContext = createContext({
  themePreference: 'system',
  resolvedTheme: 'dark',
  setThemePreference: () => {},
  toggleTheme: () => {},
});

export function ThemeProvider({ children }) {
  const [themePreference, setThemePreferenceState] = useState(() => {
    try {
      const storedPref = localStorage.getItem('aerovital_theme_preference');
      if (storedPref && ['system', 'light', 'dark'].includes(storedPref)) {
        return storedPref;
      }
      const legacyTheme = localStorage.getItem('aerovital_theme');
      if (legacyTheme && ['light', 'dark'].includes(legacyTheme)) {
        return legacyTheme;
      }
    } catch (e) {
      // Ignore localStorage failure in restricted contexts
    }
    return 'system';
  });

  const [systemIsDark, setSystemIsDark] = useState(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return true; // Default dark for aerospace cockpit if unknown
  });

  // Listen to system changes
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e) => setSystemIsDark(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Listen to cross-tab storage changes
  useEffect(() => {
    const handleStorage = (e) => {
      if (e.key === 'aerovital_theme_preference' && e.newValue) {
        if (['system', 'light', 'dark'].includes(e.newValue)) {
          setThemePreferenceState(e.newValue);
        }
      }
    };
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const resolvedTheme = useMemo(() => {
    if (themePreference === 'dark') return 'dark';
    if (themePreference === 'light') return 'light';
    return systemIsDark ? 'dark' : 'light';
  }, [themePreference, systemIsDark]);

  // Apply attributes to DOM
  useEffect(() => {
    try {
      document.documentElement.setAttribute('data-theme', resolvedTheme);
      if (resolvedTheme === 'dark') {
        document.body.classList.add('dark-theme');
      } else {
        document.body.classList.remove('dark-theme');
      }

      const meta = document.querySelector('meta[name="color-scheme"]');
      if (meta) {
        meta.content = themePreference === 'system' ? 'light dark' : resolvedTheme;
      }

      localStorage.setItem('aerovital_theme_preference', themePreference);
      localStorage.setItem('aerovital_theme', resolvedTheme);
    } catch (e) {
      // Handle storage / DOM restrictions safely
    }
  }, [resolvedTheme, themePreference]);

  const setThemePreference = useCallback((pref) => {
    if (['system', 'light', 'dark'].includes(pref)) {
      setThemePreferenceState(pref);
    }
  }, []);

  const toggleTheme = useCallback(() => {
    // When toggling from a quick button:
    // If currently dark (either via preference or resolved system), switch to light.
    // If currently light, switch to dark.
    setThemePreferenceState((prev) => {
      const currentResolved = prev === 'system' ? (systemIsDark ? 'dark' : 'light') : prev;
      return currentResolved === 'dark' ? 'light' : 'dark';
    });
  }, [systemIsDark]);

  const value = useMemo(() => ({
    themePreference,
    resolvedTheme,
    systemIsDark,
    setThemePreference,
    toggleTheme,
  }), [themePreference, resolvedTheme, systemIsDark, setThemePreference, toggleTheme]);

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export default useTheme;
