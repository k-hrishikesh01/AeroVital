import React from 'react';
import { AuthProvider, useAuth } from './hooks/useAuth';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import BrandLogo from './components/common/BrandLogo';
import './styles/theme.css';
import './styles/dashboard.css';

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--bg-app)',
        color: 'var(--text-primary)',
        gap: '20px',
        fontFamily: 'var(--font-main)'
      }}>
        <BrandLogo variant="auto" size={72} />
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
          <div style={{ fontWeight: 800, fontSize: '18px', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            AeroVital
          </div>
          <div style={{
            width: '120px',
            height: '3px',
            background: 'var(--brand-tricolour-bar)',
            borderRadius: '2px',
          }} />
          <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-secondary)', letterSpacing: '0.04em', marginTop: '4px' }}>
            Initializing AeroVital Session...
          </div>
        </div>
        <div style={{
          width: '28px',
          height: '28px',
          border: '2px solid var(--border-light)',
          borderTopColor: 'var(--text-primary)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
          marginTop: '6px'
        }}></div>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return <DashboardPage />;
}

export function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
