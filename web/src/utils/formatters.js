/**
 * Presentation Formatters for AeroVital Dashboard
 * Presentation-only helper functions.
 */

export function formatPercentage(val, decimals = 0) {
  if (val === null || val === undefined || isNaN(val)) return 'N/A';
  // If value is between 0 and 1 (like confidence or SQI), scale to 100%
  const num = val <= 1.0 && val >= 0.0 ? val * 100 : val;
  return `${num.toFixed(decimals)}%`;
}

export function formatScore(score, decimals = 1) {
  if (score === null || score === undefined || isNaN(score)) return 'N/A';
  const num = score <= 1.0 ? score * 100 : score;
  return `${num.toFixed(decimals)}%`;
}

export function formatDuration(totalSeconds) {
  if (totalSeconds === null || totalSeconds === undefined || isNaN(totalSeconds)) return '--:--:--';
  const sec = Math.max(0, Math.floor(totalSeconds));
  const hrs = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  const secs = sec % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
}

export function formatTime(isoString) {
  if (!isoString) return 'N/A';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return 'N/A';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return 'N/A';
  }
}

export function formatRelativeTime(isoString) {
  if (!isoString) return 'N/A';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return 'N/A';
    const now = new Date();
    const diffSec = Math.round((now.getTime() - date.getTime()) / 1000);
    if (diffSec < 5) return 'Just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    return `${diffHours}h ago`;
  } catch {
    return 'N/A';
  }
}

export function formatFreshness(seconds) {
  if (seconds === null || seconds === undefined) return 'Unknown freshness';
  if (seconds < 5) return 'Telemetry fresh (< 5s)';
  if (seconds < 30) return `Telemetry updated ${Math.round(seconds)}s ago`;
  if (seconds < 120) return `Telemetry stale (${Math.round(seconds)}s ago)`;
  const mins = Math.round(seconds / 60);
  return `Telemetry stale (${mins}m ago)`;
}

export function getFatigueStateConfig(state) {
  switch (state) {
    case 'NORMAL':
      return {
        label: 'NORMAL',
        sublabel: 'Physiological markers optimal',
        variant: 'normal',
        color: '#10B981',
        bgColor: 'rgba(16, 185, 129, 0.12)',
      };
    case 'ELEVATED_WORKLOAD':
      return {
        label: 'ELEVATED WORKLOAD',
        sublabel: 'Sympathetic response elevated',
        variant: 'warning',
        color: '#F59E0B',
        bgColor: 'rgba(245, 158, 11, 0.12)',
      };
    case 'FATIGUE':
      return {
        label: 'FATIGUE ADVISORY',
        sublabel: 'Elevated fatigue risk detected',
        variant: 'alert',
        color: '#EF4444',
        bgColor: 'rgba(239, 68, 68, 0.12)',
      };
    case 'INSUFFICIENT_DATA':
      return {
        label: 'INSUFFICIENT DATA',
        sublabel: 'Engine abstention: low SQI or baseline missing',
        variant: 'insufficient',
        color: '#94A3B8',
        bgColor: 'rgba(148, 163, 184, 0.12)',
      };
    default:
      return {
        label: state || 'UNKNOWN',
        sublabel: 'Awaiting backend evaluation',
        variant: 'unknown',
        color: '#64748B',
        bgColor: 'rgba(100, 116, 139, 0.12)',
      };
  }
}
