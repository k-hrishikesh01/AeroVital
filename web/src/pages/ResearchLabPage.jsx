import React, { useState, useEffect } from 'react';
import Header from '../components/Header';
import AlertsDrawer from '../components/AlertsDrawer';
import PilotProfileModal from '../components/PilotProfileModal';
import DatasetBrowser from '../components/research/DatasetBrowser';
import SignalViewer from '../components/research/SignalViewer';
import EngineExecutionBar from '../components/research/EngineExecutionBar';
import StateTimeline from '../components/research/StateTimeline';
import FactorInspector from '../components/research/FactorInspector';
import ResearchExportModal from '../components/research/ResearchExportModal';
import RunComparisonModal from '../components/research/RunComparisonModal';
import PresentationMode from '../components/research/PresentationMode';
import researchApi from '../services/researchApi';

export function ResearchLabPage({
  currentView,
  onSelectView,
  theme,
  onToggleTheme,
}) {
  // Registry & Session State
  const [manifest, setManifest] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [participantsMap, setParticipantsMap] = useState({});
  const [sessions, setSessions] = useState([]);
  const [scenarioFilter, setScenarioFilter] = useState('ALL');
  const [selectedSessionId, setSelectedSessionId] = useState('SYN-S001');

  // Timeseries & Execution State
  const [timeseriesData, setTimeseriesData] = useState([]);
  const [downsampleFactor, setDownsampleFactor] = useState(5);
  const [isLoadingTimeseries, setIsLoadingTimeseries] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [latestRun, setLatestRun] = useState(null);
  const [selectedWindow, setSelectedWindow] = useState(null);

  // Modals & Run History State
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isComparisonOpen, setIsComparisonOpen] = useState(false);
  const [isPresentationOpen, setIsPresentationOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [sessionRuns, setSessionRuns] = useState([]);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // 1. Initial Load: Manifest, Participants, and Sessions
  useEffect(() => {
    loadRegistryData();
  }, []);

  // 2. Load Timeseries & Existing Run when session changes
  useEffect(() => {
    if (selectedSessionId) {
      loadSessionTimeseries(selectedSessionId, downsampleFactor);
      loadSessionRuns(selectedSessionId);
    }
  }, [selectedSessionId, downsampleFactor]);

  const loadRegistryData = async () => {
    try {
      const [man, parts, sess] = await Promise.all([
        researchApi.getManifest(),
        researchApi.getParticipants(),
        researchApi.getSessions(),
      ]);

      setManifest(man);
      setParticipants(parts || []);
      setSessions(sess || []);

      const pMap = {};
      (parts || []).forEach(p => { pMap[p.pilot_id] = p; });
      setParticipantsMap(pMap);
    } catch (err) {
      setErrorMessage(`Failed to load research dataset registry: ${err.message}`);
    }
  };

  const loadSessionTimeseries = async (sessionId, downsample) => {
    setIsLoadingTimeseries(true);
    setErrorMessage(null);
    try {
      const response = await researchApi.getSessionTimeseries(sessionId, downsample);
      setTimeseriesData(response?.data || []);
    } catch (err) {
      setErrorMessage(`Failed to stream timeseries for session ${sessionId}: ${err.message}`);
    } finally {
      setIsLoadingTimeseries(false);
    }
  };

  const loadSessionRuns = async (sessionId) => {
    try {
      const runs = await researchApi.getRuns({ session: sessionId, limit: 10 });
      setSessionRuns(runs || []);
      if (runs && runs.length > 0) {
        // Load details for latest run
        const fullRun = await researchApi.getRun(runs[0].run_id);
        setLatestRun(fullRun);
        setSelectedWindow(null);
      } else {
        setLatestRun(null);
        setSelectedWindow(null);
      }
    } catch (err) {
      console.warn('Could not retrieve historical runs for session:', err.message);
    }
  };

  const handleExecuteSession = async (sessionId, notes) => {
    setIsExecuting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const result = await researchApi.executeSession(sessionId, notes);
      setLatestRun(result);
      setSelectedWindow(null);
      setSuccessMessage(`Engine successfully evaluated ${result.total_windows_evaluated} windows in ${result.execution_duration_sec}s (${result.throughput_samples_per_sec} smp/s).`);
      // Refresh historical runs
      loadSessionRuns(sessionId);
    } catch (err) {
      setErrorMessage(`Pipeline execution failed: ${err.message}`);
    } finally {
      setIsExecuting(false);
    }
  };

  const currentSession = sessions.find(s => s.session_id === selectedSessionId);
  const currentParticipant = currentSession ? participantsMap[currentSession.participant_id] : null;

  return (
    <div className="aerovital-research-layout">
      {/* Top Header with Cockpit/Research Lab Switcher */}
      <Header
        liveStatus="RESEARCH_MODE"
        mission={null}
        alertCount={0}
        onOpenAlerts={() => setIsAlertsOpen(true)}
        onOpenProfile={() => setIsProfileOpen(true)}
        theme={theme}
        onToggleTheme={onToggleTheme}
        currentView={currentView}
        onSelectView={onSelectView}
      />

      <main className="research-main-container">
        {/* Top Research Provenance & Isolation Banner */}
        <div className="research-isolation-banner">
          <div className="banner-left">
            <span className="research-mode-tag">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M9 3h6v2H9zM10 5v5l-5 8a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-8V5" />
              </svg>
              <span>RESEARCH LAB WORKBENCH</span>
            </span>
            <span className="dataset-id-tag">
              Dataset: <strong>{manifest?.dataset_id || 'aerovital-synthetic-v1'}</strong> (v{manifest?.schema_version || '1.0.0'})
            </span>
            <span className="provenance-tag">Seed: <strong>{manifest?.random_seed ?? '42'}</strong></span>
            <span className="record-count-tag">
              <strong>{manifest?.total_records ? `${manifest.total_records.toLocaleString()} Observations` : '216,000 Observations'}</strong> ({manifest?.total_sessions ?? 60} Sorties / {manifest?.total_participants ?? 30} Profiles)
            </span>
          </div>

          <div className="banner-right">
            <span className="isolation-indicator">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <span>STRICT OPERATIONAL ISOLATION — ZERO LIVE DATABASE WRITES</span>
            </span>
          </div>
        </div>

        {/* Global Feedback Notifications */}
        {errorMessage && (
          <div className="research-error-banner">
            <span>{errorMessage}</span>
            <button className="dismiss-btn" onClick={() => setErrorMessage(null)}>&times;</button>
          </div>
        )}
        {successMessage && (
          <div className="research-success-banner">
            <span>{successMessage}</span>
            <button className="dismiss-btn" onClick={() => setSuccessMessage(null)}>&times;</button>
          </div>
        )}

        {/* Top Operational Controls Bar */}
        <EngineExecutionBar
          selectedSessionId={selectedSessionId}
          isExecuting={isExecuting}
          onExecute={handleExecuteSession}
          latestRun={latestRun}
          onOpenExport={() => setIsExportOpen(true)}
          onOpenComparison={() => setIsComparisonOpen(true)}
          onOpenRunsHistory={() => setIsComparisonOpen(true)}
          onOpenPresentation={() => setIsPresentationOpen(true)}
        />

        {/* Two-Column Main Workbench Area */}
        <div className="research-workbench-grid">
          {/* Left Column: Dataset and Session Registry Explorer */}
          <div className="workbench-col-left">
            <DatasetBrowser
              sessions={sessions}
              selectedSessionId={selectedSessionId}
              onSelectSession={(sId) => setSelectedSessionId(sId)}
              scenarioFilter={scenarioFilter}
              onSelectScenario={(sc) => setScenarioFilter(sc)}
              participantsMap={participantsMap}
              isLoading={!sessions.length}
            />
          </div>

          {/* Right Column: Telemetry Visualizer & Engine Intelligence Suite */}
          <div className="workbench-col-right">
            {/* 1. Synchronized Signal Visualizer */}
            <SignalViewer
              session={currentSession}
              participant={currentParticipant}
              timeseriesData={timeseriesData}
              downsampleFactor={downsampleFactor}
              onChangeDownsample={(factor) => setDownsampleFactor(factor)}
              isLoadingTimeseries={isLoadingTimeseries}
              selectedTimestamp={selectedWindow?.timestamp}
              onSelectTimestamp={(ts) => {
                if (latestRun?.window_outputs) {
                  const match = latestRun.window_outputs.find(w => w.timestamp === ts);
                  if (match) setSelectedWindow(match);
                }
              }}
            />

            {/* 2. Discrete State & Confidence Timeline */}
            <StateTimeline
              run={latestRun}
              selectedWindow={selectedWindow}
              onSelectWindow={(win) => setSelectedWindow(win)}
            />

            {/* 3. Explanatory Factor Inspector Drawer */}
            <FactorInspector
              selectedWindow={selectedWindow}
              runSummary={latestRun}
            />
          </div>
        </div>
      </main>

      {/* Export Session Modal */}
      <ResearchExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        sessionId={selectedSessionId}
        sessionScenario={currentSession?.scenario || ''}
      />

      {/* Run Comparison Modal */}
      <RunComparisonModal
        isOpen={isComparisonOpen}
        onClose={() => setIsComparisonOpen(false)}
        initialRunIds={latestRun ? [latestRun.run_id] : []}
      />

      {/* Fullscreen 5-Scenario Research Demonstration Mode */}
      {isPresentationOpen && (
        <PresentationMode
          onClose={() => setIsPresentationOpen(false)}
          onSelectSession={(sId) => {
            setSelectedSessionId(sId);
            setIsPresentationOpen(false);
          }}
        />
      )}

      {/* Alerts Drawer */}
      <AlertsDrawer
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        alerts={[]}
        onAcknowledge={() => {}}
      />

      {/* Pilot Profile Modal */}
      <PilotProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
      />
    </div>
  );
}

export default ResearchLabPage;
