import React, { useState, useEffect } from 'react';
import { formatDuration } from '../utils/formatters';

export function CurrentSessionCard({ mission }) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const isActive = Boolean(mission && mission.status === 'ACTIVE' && mission.start_time);

  useEffect(() => {
    if (!isActive) {
      setElapsedSeconds(0);
      return;
    }

    const start = new Date(mission.start_time).getTime();
    const calculateElapsed = () => {
      const now = Date.now();
      const diff = Math.max(0, Math.floor((now - start) / 1000));
      setElapsedSeconds(diff);
    };
    calculateElapsed();
    const interval = setInterval(calculateElapsed, 1000);
    return () => clearInterval(interval);
  }, [isActive, mission?.start_time]);

  return (
    <article className="card-session-time" aria-label="Flight Session Elapsed Time">
      <span className="card-label">Session Elapsed Time</span>
      <div className="session-timer-display">
        {isActive ? (
          <span className="mono-num">{formatDuration(elapsedSeconds)}</span>
        ) : (
          <span className="session-inactive-label" style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Session inactive
          </span>
        )}
      </div>

      <div className="session-meta-strip">
        <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>
          {isActive
            ? `${mission.code || mission.mission_code || 'ACTIVE'} • ${mission.phase || mission.current_phase || 'Cruise'}`
            : 'No active flight mission'}
        </span>
      </div>
    </article>
  );
}

export default CurrentSessionCard;
