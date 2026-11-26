/**
 * AeroVital Research Lab API Service
 * Handles authenticated communication with /api/v1/research/ endpoints.
 */

import api, { ApiError } from './api';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

async function researchRequest(endpoint, options = {}) {
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
      `Network connection to AeroVital Research API failed: ${networkError.message}`,
      0,
      { isNetworkError: true }
    );
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || data?.error || `Research API error: HTTP ${response.status}`;
    throw new ApiError(message, response.status, data);
  }

  return data;
}

export const researchApi = {
  /**
   * Fetch dataset manifest with versioning, checksums, and isolation statement.
   */
  async getManifest() {
    return researchRequest('/api/v1/research/manifest/');
  },

  /**
   * Fetch all 30 synthetic participant profiles and baselines.
   */
  async getParticipants() {
    return researchRequest('/api/v1/research/participants/');
  },

  /**
   * Fetch sessions with optional scenario filter.
   */
  async getSessions(scenario = null) {
    const query = scenario ? `?scenario=${encodeURIComponent(scenario)}` : '';
    return researchRequest(`/api/v1/research/sessions/${query}`);
  },

  /**
   * Stream timeseries observations for a session.
   */
  async getSessionTimeseries(sessionId, downsample = 5) {
    return researchRequest(`/api/v1/research/sessions/${sessionId}/timeseries/?downsample=${downsample}`);
  },

  /**
   * Execute AeroVital Core pipeline on a session.
   */
  async executeSession(sessionId, notes = '') {
    return researchRequest('/api/v1/research/execute/', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, notes }),
    });
  },

  /**
   * List historical research runs.
   */
  async getRuns({ session, scenario, limit = 50 } = {}) {
    const params = new URLSearchParams();
    if (session) params.append('session', session);
    if (scenario) params.append('scenario', scenario);
    if (limit) params.append('limit', String(limit));
    const query = params.toString() ? `?${params.toString()}` : '';
    return researchRequest(`/api/v1/research/runs/${query}`);
  },

  /**
   * Retrieve full run detail including per-window evaluations.
   */
  async getRun(runId) {
    return researchRequest(`/api/v1/research/runs/${runId}/`);
  },

  /**
   * Compare two or more runs side-by-side.
   */
  async compareRuns(runIds) {
    const ids = Array.isArray(runIds) ? runIds.join(',') : runIds;
    return researchRequest(`/api/v1/research/runs/compare/?run_ids=${encodeURIComponent(ids)}`);
  },

  /**
   * Securely download session telemetry and evaluation via authenticated Blob request.
   * Uses existing DRF Token Authentication header; never exposes tokens in query parameters.
   */
  async downloadSessionExport(sessionId, format = 'csv') {
    const token = localStorage.getItem('aerovital_auth_token');
    const headers = {};
    if (token) {
      headers['Authorization'] = `Token ${token}`;
    }

    const url = `${API_BASE_URL}/api/v1/research/export/${sessionId}/?format=${format}`;
    let response;
    try {
      response = await fetch(url, { method: 'GET', headers });
    } catch (networkError) {
      throw new ApiError(
        `Network error during file export: ${networkError.message}`,
        0,
        { isNetworkError: true }
      );
    }

    if (!response.ok) {
      let errorDetail;
      try {
        const errJson = await response.json();
        errorDetail = errJson?.detail || errJson?.error;
      } catch {
        errorDetail = await response.text();
      }
      throw new ApiError(
        errorDetail || `Export download failed: HTTP ${response.status}`,
        response.status
      );
    }

    return await response.blob();
  },

  /**
   * Clean endpoint URL reference without token query-parameter exposure.
   */
  getExportUrl(sessionId, format = 'csv') {
    return `${API_BASE_URL}/api/v1/research/export/${sessionId}/?format=${format}`;
  },
};

export default researchApi;
