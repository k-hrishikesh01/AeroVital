import React, { useState, useEffect } from 'react';
import { formatDuration } from '../utils/formatters';

export function CurrentSessionCard({ mission }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isRunning, setIsRunning] = useState(true);

  // Compute elapsed time from mission start_time if available, else local stopwatch
  useEffect(() => {
    if (mission?.start_time) {
      const start = new Date(mission.start_time).getTime();
      const calculateElapsed = () => {
        const now = Date.now();
        const diff = Math.max(0, Math.floor((now - start) / 1000));
        setElapsedSeconds(diff);
      };
      calculateElapsed();
      const interval = setInterval(calculateElapsed, 1000);
      return () => clearInterval(interval);
    } else {
      // Local session timer fallback
      if (!isRunning) return;
      const interval = setInterval(() => {
        setElapsedSeconds(prev => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [mission?.start_time, isRunning]);

  return (
    <article className="card-session-time" aria-label="Flight Session Stopwatch">
      <span className="card-label">Session Elapsed Time</span>
      <div className="session-timer-display">
        <span className="mono-num">{formatDuration(elapsedSeconds)}</span>
      </div>

      <div className="session-meta-strip">
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {!mission?.start_time && (
            <>
              <button
                className="btn-secondary"
                style={{ padding: '4px 10px', fontSize: '11px' }}
                onClick={() => setIsRunning(prev => !prev)}
              >
                {isRunning ? 'Pause' : 'Resume'}
              </button>
              <button
                className="btn-secondary"
                style={{ padding: '4px 10px', fontSize: '11px' }}
                onClick={() => setElapsedSeconds(0)}
              >
                Reset
              </button>
            </>
          )}
        </div>
        <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
          {mission ? `${mission.status || 'Active'} • ${mission.phase || mission.current_phase || 'Cruise'}` : 'Flight Deck Active'}
        </span>
      </div>
    </article>
  );
}

export default CurrentSessionCard;
