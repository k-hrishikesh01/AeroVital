import React, { useState, useEffect } from 'react';
import useDashboardData from '../hooks/useDashboardData';
import Header from '../components/Header';
import StatusBanner from '../components/StatusBanner';
import CurrentSessionCard from '../components/CurrentSessionCard';
import CurrentStateCard from '../components/CurrentStateCard';
import TelemetryDetails from '../components/TelemetryDetails';
import VitalityTimelineChart from '../components/VitalityTimelineChart';
import TelemetryStreamChart from '../components/TelemetryStreamChart';
import AtmosphericStrip from '../components/AtmosphericStrip';
import TelemetryLogsTable from '../components/TelemetryLogsTable';
import AlertsDrawer from '../components/AlertsDrawer';
import PilotProfileModal from '../components/PilotProfileModal';
import DemoECGPanel from '../components/DemoECGPanel';

export function DashboardPage() {
  const {
    currentState,
    latestTelemetry,
    recentTelemetry,
    signalQuality,
    recentFeatures,
    estimates,
    alerts,
    missions,
    isLoading,
    isRefreshing,
    backendUnavailable,
    error,
    liveStatus,
    acknowledgeAlert,
    refetch,
  } = useDashboardData();

  const [theme, setTheme] = useState(() => localStorage.getItem('aerovital_theme') || 'light');
  const [isMobilePreview, setIsMobilePreview] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  // Apply theme to body
  useEffect(() => {
    if (theme === 'dark') {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
    localStorage.setItem('aerovital_theme', theme);
  }, [theme]);

  // Apply mobile preview mode to body
  useEffect(() => {
    if (isMobilePreview) {
      document.body.classList.add('mobile-view-mode');
    } else {
      document.body.classList.remove('mobile-view-mode');
    }
  }, [isMobilePreview]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
  };

  const toggleMobilePreview = () => {
    setIsMobilePreview(prev => !prev);
  };

  const activeMission = currentState?.mission || (missions && missions[0]) || null;
  const currentBpm = latestTelemetry?.heart_rate ? Math.round(latestTelemetry.heart_rate) : 75;

  return (
    <div className="app-layout">
      {/* Header */}
      <Header
        liveStatus={liveStatus}
        mission={activeMission}
        alertCount={alerts.length}
        onOpenAlerts={() => setIsAlertsOpen(true)}
        onOpenProfile={() => setIsProfileOpen(true)}
        theme={theme}
        onToggleTheme={toggleTheme}
        isMobilePreview={isMobilePreview}
        onToggleMobilePreview={toggleMobilePreview}
      />

      {/* Connectivity & Operational Banner */}
      <StatusBanner
        liveStatus={liveStatus}
        freshnessSec={currentState?.freshness_sec}
        isRefreshing={isRefreshing}
        onRefresh={refetch}
        errorMessage={error}
      />

      {/* Main Grid View */}
      <main className="dashboard-wrapper">
        <div className="grid-flight-deck">
          {/* Left Column: Current Flight Session & Core State */}
          <section className="screen-card-column" aria-label="Current Flight Session Telemetry">
            <h2 className="section-headline">Current Session</h2>

            <CurrentSessionCard mission={activeMission} />

            <CurrentStateCard currentState={currentState} />

            <TelemetryDetails
              latestTelemetry={latestTelemetry}
              recentFeatures={recentFeatures}
              signalQuality={signalQuality}
            />
          </section>

          {/* Right Column: Real Telemetry Stream & Historical Visualizations */}
          <section className="telemetry-column" aria-label="Advanced Biometrics & Charts">
            {/* Explicit Demo/Simulation Bench (Preserves visual work honestly without faking telemetry) */}
            <DemoECGPanel currentBpm={currentBpm} />

            {/* Real State History Timeline Chart */}
            <VitalityTimelineChart estimates={estimates} />

            {/* Real Telemetry Stream Chart */}
            <TelemetryStreamChart telemetry={recentTelemetry} />

            {/* Atmospheric and Motion Strip */}
            <AtmosphericStrip
              mission={activeMission}
              latestTelemetry={latestTelemetry}
              signalQuality={signalQuality}
            />

            {/* Historical Ingested Telemetry Table with CSV Export */}
            <TelemetryLogsTable
              telemetry={recentTelemetry}
              flightCode={activeMission?.code || 'AV-409'}
            />
          </section>
        </div>
      </main>

      {/* Slide-out Flight Safety Alerts Drawer */}
      <AlertsDrawer
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        alerts={alerts}
        onAcknowledge={acknowledgeAlert}
      />

      {/* Pilot Profile Modal */}
      <PilotProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
      />
    </div>
  );
}

export default DashboardPage;
