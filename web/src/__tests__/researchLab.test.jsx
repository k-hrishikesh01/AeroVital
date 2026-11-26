import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../App';
import { Header } from '../components/Header';
import { ResearchLabPage } from '../pages/ResearchLabPage';
import { DatasetBrowser } from '../components/research/DatasetBrowser';
import { SignalViewer } from '../components/research/SignalViewer';
import { EngineExecutionBar } from '../components/research/EngineExecutionBar';
import { StateTimeline } from '../components/research/StateTimeline';
import { FactorInspector } from '../components/research/FactorInspector';
import { ResearchExportModal } from '../components/research/ResearchExportModal';
import { RunComparisonModal } from '../components/research/RunComparisonModal';
import researchApi from '../services/researchApi';
import api from '../services/api';
import { AuthProvider } from '../hooks/useAuth';

vi.mock('../services/api', () => ({
  default: {
    auth: {
      login: vi.fn(),
      getMe: vi.fn().mockResolvedValue({
        user_id: 1,
        username: 'testpilot',
        role: 'PILOT',
        pilot: { id: 1, name: 'Capt. Test Pilot', pilot_code: 'PL-001' }
      }),
      logout: vi.fn(),
    },
    intelligence: {
      getCurrentState: vi.fn().mockResolvedValue({
        state: 'NORMAL',
        vitality_score: 88,
        confidence: 0.95,
        sqi: 0.98,
        freshness_sec: 2,
        dominant_factor: 'NONE',
        factors: { cardiac_strain: 0.1, hypoxia: 0.0, g_strain: 0.0, recovery: 0.9 }
      }),
      getEstimates: vi.fn().mockResolvedValue({}),
      getBaselines: vi.fn().mockResolvedValue({}),
    },
    telemetry: {
      getTelemetry: vi.fn().mockResolvedValue([]),
      getSignalQuality: vi.fn().mockResolvedValue([]),
      getFeatures: vi.fn().mockResolvedValue([]),
    },
    alerts: {
      getAlerts: vi.fn().mockResolvedValue([]),
      acknowledgeAlert: vi.fn().mockResolvedValue({}),
    },
    missions: {
      getMissions: vi.fn().mockResolvedValue([{ id: 1, code: 'AV-M101', phase: 'EN_ROUTE', g_load: 1.1 }]),
    },
  },
  ApiError: class ApiError extends Error {
    constructor(message, status, data) {
      super(message);
      this.status = status;
      this.data = data;
    }
  },
}));

vi.mock('../services/researchApi', () => ({
  default: {
    getManifest: vi.fn(),
    getParticipants: vi.fn(),
    getSessions: vi.fn(),
    getSessionTimeseries: vi.fn(),
    executeSession: vi.fn(),
    getRuns: vi.fn(),
    getRun: vi.fn(),
    compareRuns: vi.fn(),
    getExportUrl: vi.fn(),
    exportSession: vi.fn(),
    downloadSessionExport: vi.fn(),
  },
}));

const mockManifest = {
  dataset_id: 'aerovital-synthetic-v1',
  schema_version: '1.0.0',
  random_seed: 42,
  total_records: 216000,
  total_sessions: 60,
  total_participants: 30,
};

const mockParticipants = [
  {
    pilot_id: 'SYN-P001',
    callsign: 'VITAL-01',
    age: 27,
    resting_heart_rate: 66.7,
    baseline_rmssd: 34.9,
  },
  {
    pilot_id: 'SYN-P002',
    callsign: 'VITAL-02',
    age: 41,
    resting_heart_rate: 54.3,
    baseline_rmssd: 32.9,
  },
];

const mockSessions = [
  {
    session_id: 'SYN-S001',
    participant_id: 'SYN-P001',
    scenario: 'NORMAL_BASELINE',
    duration_sec: 3600,
    total_observations: 3600,
    hr_mean: 66.7,
    baseline_resting_hr: 66.7,
    baseline_rmssd: 34.9,
  },
  {
    session_id: 'SYN-S002',
    participant_id: 'SYN-P001',
    scenario: 'ELEVATED_COGNITIVE_WORKLOAD',
    duration_sec: 3600,
    total_observations: 3600,
    hr_mean: 92.4,
    baseline_resting_hr: 66.7,
    baseline_rmssd: 34.9,
  },
];

const mockTimeseries = {
  data: [
    {
      time_sec: 0,
      timestamp: '2026-11-20T08:00:00Z',
      heart_rate: 68.0,
      external_g_load: 1.0,
      rr_interval: [882.35],
      accel_z: 1.0,
      mission_phase: 'CRUISE',
    },
    {
      time_sec: 5,
      timestamp: '2026-11-20T08:00:05Z',
      heart_rate: 70.0,
      external_g_load: 1.0,
      rr_interval: [857.14],
      accel_z: 1.0,
      mission_phase: 'CRUISE',
    },
  ],
};

const mockRunResult = {
  run_id: 'RUN-TEST-001',
  session_id: 'SYN-S001',
  participant_id: 'SYN-P001',
  scenario: 'NORMAL_BASELINE',
  pipeline_version: '1.0.0',
  dataset_version: '1.0.0',
  execution_duration_sec: 0.88,
  throughput_samples_per_sec: 4090,
  total_windows_evaluated: 60,
  mean_confidence: 0.94,
  mean_sqi: 0.97,
  abstention_rate_pct: 0.0,
  state_breakdown: {
    NORMAL: { count: 55, percentage: 91.7 },
    ELEVATED_WORKLOAD: { count: 5, percentage: 8.3 },
  },
  dominant_factors_summary: [
    { factor: 'Physiological parameters within nominal limits', count: 55 },
  ],
  window_outputs: [
    {
      window_index: 0,
      timestamp: '2026-11-20T08:01:00Z',
      state: 'NORMAL',
      confidence: 0.95,
      sqi: 0.98,
      dominant_factors: ['Physiological parameters within nominal limits'],
      is_abstained: false,
    },
  ],
};

describe('AeroVital Research Lab Integration Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    localStorage.setItem('aerovital_auth_token', 'mock-token');

    // Setup Blob URL mocks
    window.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock-export-url');
    window.URL.revokeObjectURL = vi.fn();

    researchApi.getManifest.mockResolvedValue(mockManifest);
    researchApi.getParticipants.mockResolvedValue(mockParticipants);
    researchApi.getSessions.mockResolvedValue(mockSessions);
    researchApi.getSessionTimeseries.mockResolvedValue(mockTimeseries);
    researchApi.getRuns.mockResolvedValue([mockRunResult]);
    researchApi.getRun.mockResolvedValue(mockRunResult);
    researchApi.executeSession.mockResolvedValue(mockRunResult);
    researchApi.getExportUrl.mockReturnValue('https://api.aerovital.test/export.csv');
    researchApi.downloadSessionExport.mockResolvedValue(new Blob(['col1,col2\n'], { type: 'text/csv' }));
  });

  it('1. navigates between Operational Cockpit and Research Lab via Header mode switcher', async () => {
    render(<App />);

    // Initially loads Operational Cockpit
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /^operational cockpit$/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^research lab$/i })).toBeInTheDocument();
    });

    // Switch to Research Lab
    const researchBtn = screen.getByRole('button', { name: /^research lab$/i });
    fireEvent.click(researchBtn);

    // Verify Research Lab view rendered
    await waitFor(() => {
      expect(screen.getByText(/research lab workbench/i)).toBeInTheDocument();
      expect(screen.getByText(/strict operational isolation — zero live database writes/i)).toBeInTheDocument();
    });

    // Switch back to Operational Cockpit
    const cockpitBtn = screen.getByRole('button', { name: /^operational cockpit$/i });
    fireEvent.click(cockpitBtn);

    await waitFor(() => {
      expect(screen.getByText(/current session/i)).toBeInTheDocument();
    });
  });

  it('2. verifies Strict Operational Isolation banner and dynamic dataset provenance display', async () => {
    render(
      <AuthProvider>
        <ResearchLabPage
          currentView="research"
          onSelectView={() => {}}
          theme="dark"
          onToggleTheme={() => {}}
        />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/strict operational isolation — zero live database writes/i)).toBeInTheDocument();
      expect(screen.getByText(/aerovital-synthetic-v1/i)).toBeInTheDocument();
      expect(screen.getByText(/seed:/i)).toBeInTheDocument();
      expect(screen.getByText(/42/i)).toBeInTheDocument();
      expect(screen.getByText(/216,000 observations/i)).toBeInTheDocument();
    });
  });

  it('3. filters sessions by scenario chips in DatasetBrowser and selects a session', async () => {
    const handleSelectSession = vi.fn();
    const handleSelectScenario = vi.fn();

    const participantsMap = {
      'SYN-P001': mockParticipants[0],
      'SYN-P002': mockParticipants[1],
    };

    render(
      <DatasetBrowser
        sessions={mockSessions}
        selectedSessionId="SYN-S001"
        onSelectSession={handleSelectSession}
        scenarioFilter="ALL"
        onSelectScenario={handleSelectScenario}
        participantsMap={participantsMap}
        isLoading={false}
      />
    );

    // Verify sessions rendered
    expect(screen.getByText('SYN-S001')).toBeInTheDocument();
    expect(screen.getByText('SYN-S002')).toBeInTheDocument();

    // Click Elevated Workload scenario filter chip
    const workloadChip = screen.getByRole('button', { name: /elevated workload/i });
    fireEvent.click(workloadChip);
    expect(handleSelectScenario).toHaveBeenCalledWith('ELEVATED_COGNITIVE_WORKLOAD');

    // Click on session SYN-S002
    const sessionCard2 = screen.getByText('SYN-S002');
    fireEvent.click(sessionCard2);
    expect(handleSelectSession).toHaveBeenCalledWith('SYN-S002');
  });

  it('4. displays hardware non-fabrication protocol, supports downsampling controls, and synchronizes selected timestamp', async () => {
    const handleDownsample = vi.fn();
    const handleSelectTimestamp = vi.fn();

    render(
      <SignalViewer
        session={mockSessions[0]}
        participant={mockParticipants[0]}
        timeseriesData={mockTimeseries.data}
        downsampleFactor={5}
        onChangeDownsample={handleDownsample}
        isLoadingTimeseries={false}
        selectedTimestamp="2026-11-20T08:00:00Z"
        onSelectTimestamp={handleSelectTimestamp}
      />
    );

    // Verify hardware null notice
    expect(screen.getByText(/hardware non-fabrication protocol/i)).toBeInTheDocument();
    expect(screen.getByText(/are not continuously acquired by current watch hardware and are strictly preserved as/i)).toBeInTheDocument();

    // Verify downsample control buttons
    const btn10x = screen.getByRole('button', { name: /10x/i });
    fireEvent.click(btn10x);
    expect(handleDownsample).toHaveBeenCalledWith(10);
  });

  it('5. triggers pipeline execution via EngineExecutionBar and renders execution throughput', async () => {
    const handleExecute = vi.fn();

    render(
      <EngineExecutionBar
        selectedSessionId="SYN-S001"
        isExecuting={false}
        onExecute={handleExecute}
        latestRun={mockRunResult}
        onOpenExport={() => {}}
        onOpenComparison={() => {}}
      />
    );

    // Verify metadata display
    expect(screen.getByText(/4090 samples\/s/i)).toBeInTheDocument(); // Throughput
    expect(screen.getByText(/\(0.88s runtime\)/i)).toBeInTheDocument(); // Runtime

    // Execute button trigger
    const runBtn = screen.getByRole('button', { name: /execute pipeline/i });
    fireEvent.click(runBtn);
    expect(handleExecute).toHaveBeenCalledWith('SYN-S001', '');
  });

  it('6. renders StateTimeline with discrete state ribbons and confidence disclaimer', () => {
    const handleSelectWindow = vi.fn();

    render(
      <StateTimeline
        run={mockRunResult}
        selectedWindow={null}
        onSelectWindow={handleSelectWindow}
      />
    );

    expect(screen.getByText(/state classification timeline/i)).toBeInTheDocument();
    expect(screen.getByText(/confidence metric disclaimer/i)).toBeInTheDocument();

    // Click on ribbon segment
    const segment = screen.getByTitle(/t\+ 0m: normal/i);
    fireEvent.click(segment);
    expect(handleSelectWindow).toHaveBeenCalledWith(mockRunResult.window_outputs[0]);
  });

  it('7. displays session-level and window-level dominant factors in FactorInspector', () => {
    render(
      <FactorInspector
        selectedWindow={mockRunResult.window_outputs[0]}
        runSummary={mockRunResult}
      />
    );

    expect(screen.getByText(/window explanatory factors/i)).toBeInTheDocument();
    expect(screen.getByText(/physiological parameters within nominal limits/i)).toBeInTheDocument();
    expect(screen.getByText(/0.95/i)).toBeInTheDocument(); // confidence
  });

  it('8. executes authenticated file download via Blob and handles failure states', async () => {
    const handleClose = vi.fn();

    render(
      <ResearchExportModal
        isOpen={true}
        onClose={handleClose}
        sessionId="SYN-S001"
        sessionScenario="NORMAL_BASELINE"
      />
    );

    expect(screen.getByText(/export research session data/i)).toBeInTheDocument();
    expect(screen.getByText(/tabular csv/i)).toBeInTheDocument();
    expect(screen.getByText(/structured json/i)).toBeInTheDocument();

    // Trigger authenticated download
    const downloadBtn = screen.getByRole('button', { name: /download csv/i });
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(researchApi.downloadSessionExport).toHaveBeenCalledWith('SYN-S001', 'csv');
      expect(window.URL.createObjectURL).toHaveBeenCalled();
    });
  });

  it('9. opens RunComparisonModal and evaluates output congruence between runs', async () => {
    const handleClose = vi.fn();
    const runA = mockRunResult;
    const runB = {
      ...mockRunResult,
      run_id: 'RUN-TEST-002',
      pipeline_version: '0.9.0',
    };

    researchApi.compareRuns.mockResolvedValue({
      comparison_count: 2,
      version_differences: {
        engine_version_diff: true,
        dataset_version_diff: false,
        scenario_diff: false,
      },
      runs: [runA, runB],
    });

    render(
      <RunComparisonModal
        isOpen={true}
        onClose={handleClose}
        initialRunIds={['RUN-TEST-001', 'RUN-TEST-002']}
      />
    );

    expect(screen.getByText(/compare research pipeline runs/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/engine version divergence/i)).toBeInTheDocument();
    });
  });

  it('10. verifies mobile view switching via Header dropdown menu', async () => {
    const handleSelectView = vi.fn();

    render(
      <AuthProvider>
        <Header
          liveStatus="LIVE"
          mission={null}
          alertCount={0}
          onOpenAlerts={() => {}}
          onOpenProfile={() => {}}
          theme="dark"
          onToggleTheme={() => {}}
          currentView="cockpit"
          onSelectView={handleSelectView}
        />
      </AuthProvider>
    );

    // Open user menu
    const avatarBtn = screen.getByTitle(/pilot account details/i);
    fireEvent.click(avatarBtn);

    // Verify mobile view switch button exists inside menu
    const switchBtn = screen.getByRole('button', { name: /switch to research lab/i });
    expect(switchBtn).toBeInTheDocument();

    // Click switch button
    fireEvent.click(switchBtn);
    expect(handleSelectView).toHaveBeenCalledWith('research');
  });

  it('11. renders export download error message on API failure', async () => {
    researchApi.downloadSessionExport.mockRejectedValueOnce(new Error('Server storage timeout'));

    render(
      <ResearchExportModal
        isOpen={true}
        onClose={() => {}}
        sessionId="SYN-S001"
        sessionScenario="NORMAL_BASELINE"
      />
    );

    const downloadBtn = screen.getByRole('button', { name: /download csv/i });
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(screen.getByText(/server storage timeout/i)).toBeInTheDocument();
    });
  });
});
