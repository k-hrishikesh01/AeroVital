/**
 * DATA SOURCE: /api/v1/telemetry/
 * - item.timestamp -> X-axis time label
 * - item.heart_rate -> Heart Rate Line (BPM, left axis)
 * - item.spo2 -> SpO2 Line (%, right axis)
 *
 * TRANSFORMATION: Presentation-only time formatting and axis routing.
 * Strictly consumes real ingested packets. Zero synthetic noise injection.
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

export function TelemetryStreamChart({ telemetry = [] }) {
  // Sort chronologically for streaming view
  const chartData = [...telemetry]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map(sample => ({
      time: formatTime(sample.timestamp),
      hr: sample.heart_rate !== null && sample.heart_rate !== undefined ? Math.round(sample.heart_rate) : null,
      spo2: sample.spo2 !== null && sample.spo2 !== undefined ? Number(sample.spo2.toFixed(1)) : null,
    }));

  return (
    <article className="chart-card" aria-label="Real Telemetry Biometric Stream">
      <div className="chart-header">
        <div>
          <h3 className="chart-title">Real-Time Telemetry Stream</h3>
          <span className="chart-subtitle">
            Physiological samples ingested by backend (/api/v1/telemetry/)
          </span>
        </div>
      </div>

      <div className="chart-canvas-wrapper" style={{ minHeight: '240px' }}>
        {chartData.length === 0 ? (
          <div className="empty-chart-state">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            <span>Awaiting telemetry samples from flight deck sensors...</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
              <XAxis dataKey="time" stroke="var(--text-secondary)" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="hr" domain={['auto', 'auto']} stroke="var(--text-secondary)" tick={{ fontSize: 11 }} unit=" bpm" />
              <YAxis yAxisId="spo2" orientation="right" domain={[85, 100]} stroke="var(--text-secondary)" tick={{ fontSize: 11 }} unit="%" />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--bg-card)',
                  borderColor: 'var(--border-light)',
                  borderRadius: '10px',
                  boxShadow: 'var(--shadow-card)',
                  color: 'var(--text-primary)',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Line
                yAxisId="hr"
                type="monotone"
                dataKey="hr"
                name="Heart Rate (BPM)"
                stroke="#EF4444"
                strokeWidth={2}
                dot={{ r: 2 }}
                connectNulls={false}
                isAnimationActive={false}
              />
              <Line
                yAxisId="spo2"
                type="monotone"
                dataKey="spo2"
                name="Oxygen Saturation (%)"
                stroke="#0EA5E9"
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </article>
  );
}

export default TelemetryStreamChart;
