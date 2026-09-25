import { useState, useEffect, useCallback, useRef } from 'react';
import api, { ApiError } from '../services/api';

export function useDashboardData(selectedMissionId = null) {
  const [currentState, setCurrentState] = useState(null);
  const [recentTelemetry, setRecentTelemetry] = useState([]);
  const [signalQuality, setSignalQuality] = useState(null);
  const [recentFeatures, setRecentFeatures] = useState(null);
  const [estimates, setEstimates] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [missions, setMissions] = useState([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [backendUnavailable, setBackendUnavailable] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetched, setLastFetched] = useState(null);

  const isMountedRef = useRef(true);

  const fetchDashboardData = useCallback(async (isInitial = false) => {
    if (!isMountedRef.current) return;
    if (isInitial) setIsLoading(true);
    else setIsRefreshing(true);

    try {
      const results = await Promise.allSettled([
        api.intelligence.getCurrentState({ missionId: selectedMissionId }),
        api.telemetry.getTelemetry({ missionId: selectedMissionId, limit: 30 }),
        api.telemetry.getSignalQuality({ missionId: selectedMissionId }),
        api.telemetry.getFeatures({ missionId: selectedMissionId }),
        api.intelligence.getEstimates({ missionId: selectedMissionId, limit: 40 }),
        api.alerts.getAlerts({ missionId: selectedMissionId, unacknowledged: true }),
        api.missions.getMissions(),
      ]);

      if (!isMountedRef.current) return;

      const [
        currentStateRes,
        telemetryRes,
        qualityRes,
        featuresRes,
        estimatesRes,
        alertsRes,
        missionsRes,
      ] = results;

      // Check if all or primary network requests failed with network error
      const hasNetworkFailure = results.some(
        r => r.status === 'rejected' && r.reason?.data?.isNetworkError
      );
      setBackendUnavailable(hasNetworkFailure);

      if (currentStateRes.status === 'fulfilled') {
        setCurrentState(currentStateRes.value);
      }
      if (telemetryRes.status === 'fulfilled') {
        const telList = Array.isArray(telemetryRes.value) ? telemetryRes.value : [];
        setRecentTelemetry(telList);
      }
      if (qualityRes.status === 'fulfilled') {
        const qList = Array.isArray(qualityRes.value) ? qualityRes.value : [];
        setSignalQuality(qList[0] || null);
      }
      if (featuresRes.status === 'fulfilled') {
        const featList = Array.isArray(featuresRes.value) ? featuresRes.value : [];
        setRecentFeatures(featList[0] || null);
      }
      if (estimatesRes.status === 'fulfilled') {
        const estList = Array.isArray(estimatesRes.value) ? estimatesRes.value : [];
        setEstimates(estList);
      }
      if (alertsRes.status === 'fulfilled') {
        const alertList = Array.isArray(alertsRes.value) ? alertsRes.value : [];
        setAlerts(alertList);
      }
      if (missionsRes.status === 'fulfilled') {
        const mList = Array.isArray(missionsRes.value) ? missionsRes.value : [];
        setMissions(mList);
      }

      setError(null);
      setLastFetched(new Date());
    } catch (err) {
      if (isMountedRef.current) {
        setError(err.message || 'Failed to fetch dashboard data');
        if (err?.data?.isNetworkError) {
          setBackendUnavailable(true);
        }
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [selectedMissionId]);

  // Initial fetch and polling every 4 seconds
  useEffect(() => {
    isMountedRef.current = true;
    fetchDashboardData(true);

    const interval = setInterval(() => {
      // Don't poll if browser tab is hidden
      if (document.hidden) return;
      fetchDashboardData(false);
    }, 4000);

    return () => {
      isMountedRef.current = false;
      clearInterval(interval);
    };
  }, [fetchDashboardData]);

  // Acknowledge alert helper
  const acknowledgeAlert = async (alertId) => {
    try {
      const updated = await api.alerts.acknowledgeAlert(alertId);
      setAlerts(prev => prev.filter(a => a.id !== alertId));
      return updated;
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
      throw err;
    }
  };

  // Derive explicit system state
  let liveStatus = 'READY';
  if (backendUnavailable) {
    liveStatus = 'BACKEND_UNAVAILABLE';
  } else if (!currentState || (!currentState.last_telemetry_timestamp && recentTelemetry.length === 0)) {
    liveStatus = 'NO_TELEMETRY';
  } else if (currentState.current_state === 'INSUFFICIENT_DATA') {
    liveStatus = 'INSUFFICIENT_DATA';
  } else if (currentState.freshness_sec !== null && currentState.freshness_sec !== undefined && currentState.freshness_sec > 30) {
    liveStatus = 'STALE';
  } else if (currentState.freshness_sec !== null && currentState.freshness_sec <= 30) {
    liveStatus = 'LIVE';
  }

  const latestTelemetry = recentTelemetry[0] || null;

  return {
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
    lastFetched,
    liveStatus,
    acknowledgeAlert,
    refetch: () => fetchDashboardData(false),
  };
}

export default useDashboardData;
