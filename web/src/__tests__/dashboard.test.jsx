import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CurrentStateCard } from '../components/CurrentStateCard';
import { TelemetryDetails } from '../components/TelemetryDetails';
import { StatusBanner } from '../components/StatusBanner';
import { AlertsDrawer } from '../components/AlertsDrawer';
import { LoginPage } from '../pages/LoginPage';
import { App } from '../App';
import { AuthProvider } from '../hooks/useAuth';
import api from '../services/api';
import { formatScore, formatPercentage, formatTime, getFatigueStateConfig } from '../utils/formatters';

vi.mock('../services/api', () => ({
  default: {
    auth: {
      login: vi.fn(),
      getMe: vi.fn(),
      logout: vi.fn(),
    },
    intelligence: {
      getCurrentState: vi.fn(),
      getEstimates: vi.fn(),
      getBaselines: vi.fn(),
    },
    telemetry: {
      getTelemetry: vi.fn(),
      getSignalQuality: vi.fn(),
      getFeatures: vi.fn(),
    },
    alerts: {
      getAlerts: vi.fn(),
      acknowledgeAlert: vi.fn(),
    },
    missions: {
      getMissions: vi.fn(),
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

describe('AeroVital Dashboard Comprehensive Test Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  // 1. Authentication Failure
  it('1. renders authentication failure error message when login fails', async () => {
    api.auth.login.mockRejectedValueOnce(new Error('Invalid credentials.'));

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const userInput = screen.getByLabelText(/username/i);
    const passInput = screen.getByLabelText(/password/i);
    const submitBtn = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(userInput, { target: { value: 'wrong_pilot' } });
    fireEvent.change(passInput, { target: { value: 'bad_password' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/invalid credentials/i);
    });
  });

  // 2. Loading State
  it('2. displays loading state while session is initializing', () => {
    // getMe does not resolve immediately
    api.auth.getMe.mockReturnValue(new Promise(() => {}));
    localStorage.setItem('aerovital_auth_token', 'test-token');

    render(<App />);
    expect(screen.getByText(/initializing aerovital session/i)).toBeInTheDocument();
  });

  // 3. Backend Unavailable
  it('3. renders backend offline state when connection fails', () => {
    render(
      <StatusBanner
        liveStatus="BACKEND_UNAVAILABLE"
        freshnessSec={null}
        isRefreshing={false}
        onRefresh={() => {}}
        errorMessage="Network error"
      />
    );

    expect(screen.getByText(/backend offline/i)).toBeInTheDocument();
    expect(screen.getByText(/network error/i)).toBeInTheDocument();
  });

  // 4. INSUFFICIENT_DATA Rendering
  it('4. renders INSUFFICIENT_DATA state cleanly without calculations or errors', () => {
    const insufficientState = {
      current_state: 'INSUFFICIENT_DATA',
      fatigue_score: null,
      confidence: 0.22,
      overall_sqi: 0.35,
      dominant_factors: ['Engine abstention: low sensor quality (SQI < 0.40)'],
      baseline_version: '1.0',
      timestamp: '2026-09-25T12:00:00Z',
    };

    render(<CurrentStateCard currentState={insufficientState} />);

    // Must show INSUFFICIENT DATA
    expect(screen.getByText('INSUFFICIENT DATA')).toBeInTheDocument();
    // Must show N/A for fatigue score, not 0
    expect(screen.getByText('N/A')).toBeInTheDocument();
    // Must show confidence as 22%
    expect(screen.getByText('22%')).toBeInTheDocument();
    // Must show SQI as 35%
    expect(screen.getByText(/SQI: 35%/i)).toBeInTheDocument();
    // Must show the engine abstention factor
    expect(screen.getByText(/low sensor quality/i)).toBeInTheDocument();
  });

  // 5. NORMAL / Current-State Rendering
  it('5. renders NORMAL current-state with score, confidence, SQI, and factors', () => {
    const normalState = {
      current_state: 'NORMAL',
      fatigue_score: 0.224,
      confidence: 0.88,
      overall_sqi: 0.95,
      dominant_factors: ['Circadian alertness peak', 'Resting cardiac baseline aligned'],
      baseline_version: '1.0',
      timestamp: '2026-09-25T12:00:00Z',
    };

    render(<CurrentStateCard currentState={normalState} />);

    expect(screen.getAllByText('NORMAL').length).toBeGreaterThan(0);
    expect(screen.getByText('22.4%')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
    expect(screen.getByText(/SQI: 95%/i)).toBeInTheDocument();
    expect(screen.getByText('Circadian alertness peak')).toBeInTheDocument();
  });

  // 6. Telemetry Unavailable Fields
  it('6. displays "N/A" for unavailable telemetry channels without zero substitution or random numbers', () => {
    const emptyTelemetry = {
      heart_rate: null,
      spo2: null,
      skin_temperature: null,
      rr_interval: null,
      activity_level: null,
    };

    render(
      <TelemetryDetails
        latestTelemetry={emptyTelemetry}
        recentFeatures={null}
        signalQuality={null}
      />
    );

    // Heart Rate, SpO2, Skin Temp, HRV must all show N/A
    const naElements = screen.getAllByText('N/A');
    expect(naElements.length).toBeGreaterThanOrEqual(4);
  });

  // 7. Real API Response Mapping
  it('7. verifies formatters map real backend data structures accurately', () => {
    // Score scaling: continuous [0.0, 1.0] -> percentage string
    expect(formatScore(0.456)).toBe('45.6%');
    expect(formatScore(null)).toBe('N/A');
    expect(formatPercentage(0.92)).toBe('92%');
    expect(formatPercentage(null)).toBe('N/A');

    // FatigueState configuration maps Core enums
    expect(getFatigueStateConfig('NORMAL').variant).toBe('normal');
    expect(getFatigueStateConfig('ELEVATED_WORKLOAD').variant).toBe('warning');
    expect(getFatigueStateConfig('FATIGUE').variant).toBe('alert');
    expect(getFatigueStateConfig('INSUFFICIENT_DATA').variant).toBe('insufficient');
  });

  // 8. Alert Rendering & Acknowledgment
  it('8. renders alerts from backend and allows acknowledging them', async () => {
    const mockAlerts = [
      {
        id: 'alert-1',
        alert_type: 'FATIGUE_WARNING',
        severity: 'WARNING',
        message: 'Elevated pilot fatigue risk detected by Core engine',
        trigger_state: 'ELEVATED_WORKLOAD',
        confidence: 0.85,
        acknowledged: false,
        timestamp: new Date().toISOString(),
      },
    ];

    const ackFn = vi.fn();

    render(
      <AlertsDrawer
        isOpen={true}
        onClose={() => {}}
        alerts={mockAlerts}
        onAcknowledge={ackFn}
      />
    );

    expect(screen.getByText(/FATIGUE_WARNING/i)).toBeInTheDocument();
    expect(screen.getByText('WARNING')).toBeInTheDocument();
    expect(screen.getByText(/elevated pilot fatigue risk/i)).toBeInTheDocument();

    const ackBtn = screen.getByRole('button', { name: /acknowledge/i });
    fireEvent.click(ackBtn);
    expect(ackFn).toHaveBeenCalledWith('alert-1');
  });
});
