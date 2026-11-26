import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';

export function StateTimeline({
  run,
  selectedWindow,
  onSelectWindow,
}) {
  if (!run || !run.window_outputs || !run.window_outputs.length) {
    return (
      <div className="research-card state-timeline-card empty">
        <div className="card-header-clean">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="research-badge-accent">STATE CLASSIFICATION TIMELINE</span>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Engine Evaluation</h3>
          </div>
        </div>
        <div className="research-empty-state">
          <span>Click <strong>"Execute Pipeline"</strong> to run the AeroVital Core Intelligence Engine on this session.</span>
        </div>
      </div>
    );
  }

  const windows = run.window_outputs;
  const breakdown = run.state_breakdown || {};

  // Downsample window outputs for smooth SVG rendering (1 in 5 windows)
  const timelinePoints = windows.filter((_, idx) => idx % 5 === 0).map((w, idx) => ({
    timeMins: Number((idx * 5 / 60.0).toFixed(1)),
    timestamp: w.timestamp,
    state: w.state,
    confidence: w.confidence,
    sqi: w.sqi,
    factors: w.dominant_factors,
    raw: w,
  }));

  const getStateColor = (state) => {
    switch (state) {
      case 'NORMAL': return 'var(--color-normal)';
      case 'ELEVATED_WORKLOAD': return 'var(--brand-saffron)';
      case 'FATIGUE': return 'var(--color-warning)';
      case 'INSUFFICIENT_DATA': return 'var(--color-insufficient)';
      default: return 'var(--border-light)';
    }
  };

  const CustomTimelineTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const pt = payload[0].payload;

    return (
      <div className="custom-chart-tooltip">
        <div style={{ fontWeight: 700, fontSize: '12px', borderBottom: '1px solid var(--border-light)', paddingBottom: '4px', marginBottom: '4px' }}>
          T+ {pt.timeMins} min — <span style={{ color: getStateColor(pt.state) }}>{pt.state}</span>
        </div>
        <div style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <div>Confidence Score: <strong>{pt.confidence}</strong> (Index [0–1])</div>
          <div>Signal Quality (SQI): <strong>{pt.sqi}</strong></div>
          {pt.factors && pt.factors.length > 0 && (
            <div style={{ marginTop: '4px', fontStyle: 'italic', color: 'var(--text-secondary)' }}>
              "{pt.factors[0]}"
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="research-card state-timeline-card">
      <div className="card-header-clean">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="research-badge-accent">STATE CLASSIFICATION TIMELINE</span>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>
            Run {run.run_id} ({windows.length} Windows Evaluated)
          </h3>
        </div>

        {/* State Share Summary Badges */}
        <div className="state-share-badges">
          {Object.entries(breakdown).map(([st, stat]) => (
            <div key={st} className="state-pill" style={{ borderColor: getStateColor(st) }}>
              <span className="dot" style={{ backgroundColor: getStateColor(st) }} />
              <span className="name">{st}:</span>
              <strong>{stat.percentage}%</strong>
            </div>
          ))}
        </div>
      </div>

      {/* Discrete State Ribbon */}
      <div className="state-ribbon-container">
        <div className="ribbon-label">Discrete State:</div>
        <div className="ribbon-bar">
          {timelinePoints.map((pt, i) => {
            const isSelected = selectedWindow?.timestamp === pt.timestamp;
            return (
              <div
                key={i}
                className={`ribbon-segment ${pt.state.toLowerCase()} ${isSelected ? 'selected' : ''}`}
                style={{ backgroundColor: getStateColor(pt.state) }}
                onClick={() => onSelectWindow(pt.raw)}
                title={`T+ ${pt.timeMins}m: ${pt.state} (Click to inspect factors)`}
              />
            );
          })}
        </div>
      </div>

      {/* Confidence and SQI Curves */}
      <div className="confidence-chart-viewport">
        <ResponsiveContainer width="100%" height={160}>
          <ComposedChart data={timelinePoints} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" opacity={0.4} />
            <XAxis dataKey="timeMins" unit="m" stroke="var(--text-muted)" fontSize={10} />
            <YAxis domain={[0.4, 1.0]} stroke="var(--text-muted)" fontSize={10} tickCount={4} />
            <Tooltip content={<CustomTimelineTooltip />} />
            <Line
              type="monotone"
              dataKey="confidence"
              name="Confidence Score"
              stroke="var(--brand-saffron)"
              strokeWidth={1.8}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="sqi"
              name="Composite SQI"
              stroke="var(--color-cyan)"
              strokeWidth={1.2}
              dot={false}
              opacity={0.8}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Confidence Score Disclaimer */}
      <div className="confidence-disclaimer-strip">
        <span>⚠️ <strong>Confidence Metric Disclaimer:</strong> Confidence is an engineering heuristic score [0.0–1.0] reflecting input data quality and completeness, not a calibrated statistical probability.</span>
      </div>
    </div>
  );
}

export default StateTimeline;
