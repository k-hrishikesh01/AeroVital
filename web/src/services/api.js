/**
 * AeroVital API Client Service Layer
 * Consumes the verified Django REST backend at /api/v1/
 *
 * Configurable via VITE_API_BASE_URL environment variable.
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Low-level HTTP request helper
 */
async function request(endpoint, options = {}) {
  const token = localStorage.getItem('aerovital_auth_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Token ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (networkError) {
    throw new ApiError(
      `Network connection to AeroVital backend failed: ${networkError.message}`,
      0,
      { isNetworkError: true }
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null;
  }

  let data = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const errorMsg = (data && (data.detail || data.message || JSON.stringify(data))) || `Request failed with status ${response.status}`;
    // If token is invalid or expired, clear it
    if (response.status === 401 && token) {
      localStorage.removeItem('aerovital_auth_token');
      window.dispatchEvent(new CustomEvent('aerovital:auth_expired'));
    }
    throw new ApiError(errorMsg, response.status, data);
  }

  return data;
}

export const api = {
  baseUrl: API_BASE_URL,

  auth: {
    async login(username, password) {
      const data = await request('/api/v1/auth/token/', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      if (data?.token) {
        localStorage.setItem('aerovital_auth_token', data.token);
      }
      return data;
    },

    async getMe() {
      return request('/api/v1/auth/me/');
    },

    async logout() {
      try {
        await request('/api/v1/auth/logout/', { method: 'POST' });
      } finally {
        localStorage.removeItem('aerovital_auth_token');
      }
    },
  },

  intelligence: {
    async getCurrentState({ missionId, pilotId } = {}) {
      const params = new URLSearchParams();
      if (missionId) params.append('mission', missionId);
      if (pilotId) params.append('pilot', pilotId);
      const query = params.toString() ? `?${params.toString()}` : '';
      return request(`/api/v1/intelligence/current-state/${query}`);
    },

    async getEstimates({ missionId, fatigueState, limit = 100 } = {}) {
      const params = new URLSearchParams();
      if (missionId) params.append('mission', missionId);
      if (fatigueState) params.append('fatigue_state', fatigueState);
      if (limit) params.append('limit', limit);
      const query = params.toString() ? `?${params.toString()}` : '';
      return request(`/api/v1/intelligence/estimates/${query}`);
    },

    async getBaselines() {
      return request('/api/v1/intelligence/baselines/');
    },
  },

  telemetry: {
    async getTelemetry({ missionId, deviceId, limit = 50 } = {}) {
      const params = new URLSearchParams();
      if (missionId) params.append('mission', missionId);
      if (deviceId) params.append('device', deviceId);
      if (limit) params.append('limit', limit);
      const query = params.toString() ? `?${params.toString()}` : '';
      return request(`/api/v1/telemetry/${query}`);
    },

    async getSignalQuality({ missionId } = {}) {
      const params = new URLSearchParams();
      if (missionId) params.append('mission', missionId);
      const query = params.toString() ? `?${params.toString()}` : '';
      return request(`/api/v1/telemetry/signal-quality/${query}`);
    },

    async getFeatures({ missionId } = {}) {
      const params = new URLSearchParams();
      if (missionId) params.append('mission', missionId);
      const query = params.toString() ? `?${params.toString()}` : '';
      return request(`/api/v1/telemetry/features/${query}`);
    },
  },

  alerts: {
    async getAlerts({ missionId, severity, unacknowledged } = {}) {
      const params = new URLSearchParams();
      if (missionId) params.append('mission', missionId);
      if (severity) params.append('severity', severity);
      if (unacknowledged !== undefined) params.append('unacknowledged', String(unacknowledged));
      const query = params.toString() ? `?${params.toString()}` : '';
      return request(`/api/v1/alerts/${query}`);
    },

    async acknowledgeAlert(alertId) {
      return request(`/api/v1/alerts/${alertId}/acknowledge/`, {
        method: 'POST',
      });
    },
  },

  missions: {
    async getMissions() {
      return request('/api/v1/missions/');
    },

    async getMission(id) {
      return request(`/api/v1/missions/${id}/`);
    },
  },

  pilots: {
    async getPilots() {
      return request('/api/v1/pilots/');
    },

    async getPilot(id) {
      return request(`/api/v1/pilots/${id}/`);
    },
  },

  devices: {
    async getDevices() {
      return request('/api/v1/devices/');
    },
  },
};

export { ApiError };
export default api;
