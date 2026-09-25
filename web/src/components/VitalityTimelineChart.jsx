/**
 * DATA SOURCE: /api/v1/intelligence/estimates/
 * - item.timestamp -> X-axis time label
 * - item.fatigue_score -> Fatigue Score Line (scaled [0.0, 1.0] -> [0, 100%])
 * - item.confidence -> Confidence Line (scaled [0.0, 1.0] -> [0, 100%])
 * - item.overall_sqi -> SQI Line (scaled [0.0, 1.0] -> [0, 100%])
 *
 * TRANSFORMATION: Presentation-only time formatting and percentage scaling.
 * No intelligence or threshold derivations in frontend.
 */

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { formatTime } from '../utils/formatters';

export function VitalityTimelineChart({ estimates = [] }) {
  // Sort chronologically (oldest to newest for timeline presentation)
  const chartData = [...estimates]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map(est => ({
      time: formatTime(est.timestamp),
      fatigueScore: est.fatigue_score !== null && est.fatigue_score !== undefined
        ? Number((est.fatigue_score * 100).toFixed(1))
        : null,
      confidence: Number((est.confidence * 100).toFixed(1)),
      sqi: Number((est.overall_sqi * 100).toFixed(1)),
      state: est.fatigue_state,
    }));

  return (
    <article className="chart-card" aria-label="Historical Fatigue Estimation Timeline">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Flight Vitality & State Timeline</h3>
          <span className="chart-subtitle">
            Backend historical state estimates (/api/v1/intelligence/estimates/)
          </span>
        </div>
      </div>

      <div className="chart-canvas-wrapper" style={{ minHeight: '260px' }}>
        {chartData.length === 0 ? (
          <div className="empty-chart-state">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M3 3v18h18"></path>
              <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"></path>
            </svg>
            <span>No historical intelligence estimates recorded for this mission yet.</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
              <XAxis dataKey="time" stroke="var(--text-secondary)" tick={{ fontSize: 11 }} />
              <YAxis domain={[0, 100]} stroke="var(--text-secondary)" tick={{ fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-card)',
                  borderColor: 'var(--border-light)',
                  borderRadius: '10px',
                  boxShadow: 'var(--shadow-card)',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                }}
                formatter={(val, name) => [`${val}%`, name]}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Line
                type="monotone"
                dataKey="fatigueScore"
                name="Fatigue Score"
                stroke="#EF4444"
                strokeWidth={2.5}
                dot={{ r: 3 }}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="confidence"
                name="Confidence"
                stroke="#0EA5E9"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="sqi"
                name="Signal Quality (SQI)"
                stroke="#10B981"
                strokeWidth={1.8}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </article>
  );
}

export default VitalityTimelineChart;
