import React, { useState, useEffect } from 'react';
import useDashboardData from '../hooks/useDashboardData';
import { useTheme } from '../context/ThemeContext';
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
import ECGStatusPanel from '../components/DemoECGPanel';

export function DashboardPage({
  currentView = 'cockpit',
  onSelectView,
  theme: propTheme,
  onToggleTheme: propToggleTheme,
} = {}) {
  const {
    currentState,
    latestTelemetry,
    latestHeartRate,
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

  const { resolvedTheme, toggleTheme } = useTheme();
  const [isMobilePreview, setIsMobilePreview] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const activeTheme = propTheme || resolvedTheme;

  // Apply mobile preview mode to body and clean up on unmount
  useEffect(() => {
    if (isMobilePreview) {
      document.body.classList.add('mobile-view-mode');
    } else {
      document.body.classList.remove('mobile-view-mode');
    }
    return () => {
      document.body.classList.remove('mobile-view-mode');
    };
  }, [isMobilePreview]);

  const handleToggleTheme = () => {
    if (propToggleTheme) {
      propToggleTheme();
    } else {
      toggleTheme();
    }
  };

  const toggleMobilePreview = () => {
    setIsMobilePreview((prev) => !prev);
  };

  const activeMission =
    (currentState?.mission?.status === 'ACTIVE' ? currentState.mission : null) ||
    (missions && missions.find((m) => m.status === 'ACTIVE' && (!m.end_time || new Date(m.end_time) > new Date()))) ||
    null;

  return (
    <div className="app-layout">
      {/* Aviation Command Header */}
      <Header
        liveStatus={liveStatus}
        mission={activeMission}
        alertCount={alerts.length}
        onOpenAlerts={() => setIsAlertsOpen(true)}
        onOpenProfile={() => setIsProfileOpen(true)}
        theme={activeTheme}
        onToggleTheme={handleToggleTheme}
        isMobilePreview={isMobilePreview}
        onToggleMobilePreview={toggleMobilePreview}
        currentView={currentView}
        onSelectView={onSelectView}
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
              latestHeartRate={latestHeartRate}
              recentFeatures={recentFeatures}
              signalQuality={signalQuality}
            />
          </section>

          {/* Right Column: Real Telemetry Stream & Historical Visualizations */}
          <section className="telemetry-column" aria-label="Advanced Biometrics & Charts">
            {/* Honest ECG Hardware Availability Status (Acquisition does not provide Lead-II) */}
            <ECGStatusPanel />

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
