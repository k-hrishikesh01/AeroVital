import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from 'recharts';

export function SignalViewer({
  session,
  participant,
  timeseriesData,
  downsampleFactor,
  onChangeDownsample,
  isLoadingTimeseries,
  selectedTimestamp,
  onSelectTimestamp,
}) {
  const [activeTab, setActiveTab] = useState('heart_rate'); // 'heart_rate' | 'rr_interval' | 'acceleration'

  const baseHR = session?.baseline_resting_hr || participant?.resting_heart_rate || 65.0;
  const baseRMSSD = session?.baseline_rmssd || participant?.baseline_rmssd || 45.0;

  // Format data for chart display
  const chartData = (timeseriesData || []).map(d => ({
    timeMins: Number((d.time_sec / 60.0).toFixed(1)),
    timeSec: d.time_sec,
    timestamp: d.timestamp,
    heartRate: d.heart_rate,
    gLoad: d.external_g_load,
    phase: d.mission_phase,
    rrInterval: Array.isArray(d.rr_interval) ? d.rr_interval[0] : d.rr_interval,
    accelZ: d.accel_z,
  }));

  // Find timeMins corresponding to selectedTimestamp if set
  const selectedPoint = selectedTimestamp
    ? chartData.find(d => d.timestamp === selectedTimestamp)
    : null;
  const selectedTimeMins = selectedPoint ? selectedPoint.timeMins : null;

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;
    const pt = payload[0].payload;

    return (
      <div className="custom-chart-tooltip">
        <div style={{ fontWeight: 700, fontSize: '12px', borderBottom: '1px solid var(--border-light)', paddingBottom: '4px', marginBottom: '6px' }}>
          T+ {pt.timeMins} min ({pt.timeSec}s) — {pt.phase || 'N/A'}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '11px' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Heart Rate: </span>
            <strong>{pt.heartRate !== null ? `${pt.heartRate} BPM` : 'DROPOUT (N/A)'}</strong>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Airframe G-Force: </span>
            <strong>{pt.gLoad !== null ? `${pt.gLoad} G` : 'N/A'}</strong>
          </div>
          {pt.rrInterval && (
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Beat Interval: </span>
              <strong>{pt.rrInterval} ms</strong>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="research-card signal-viewer-card">
      <div className="card-header-clean">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="research-badge-accent">SIGNAL VISUALIZER</span>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>
            {session ? `${session.session_id} — ${session.scenario}` : 'Select a Session'}
          </h3>
        </div>

        {/* Downsample resolution selector */}
        <div className="downsample-controls">
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginRight: '4px' }}>Resolution:</span>
          {[
            { factor: 1, label: '1x (Full 1 Hz)' },
            { factor: 5, label: '5x (720 pts)' },
            { factor: 10, label: '10x (360 pts)' },
          ].map(opt => (
            <button
              key={opt.factor}
              className={`resolution-btn ${downsampleFactor === opt.factor ? 'active' : ''}`}
              onClick={() => onChangeDownsample(opt.factor)}
              disabled={isLoadingTimeseries}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Signal Type Selector Tabs */}
      <div className="signal-tabs-bar">
        <button
          className={`signal-tab ${activeTab === 'heart_rate' ? 'active' : ''}`}
          onClick={() => setActiveTab('heart_rate')}
        >
          Heart Rate & G-Load
        </button>
        <button
          className={`signal-tab ${activeTab === 'rr_interval' ? 'active' : ''}`}
          onClick={() => setActiveTab('rr_interval')}
        >
          Beat-to-Beat RR Intervals
        </button>
        <button
          className={`signal-tab ${activeTab === 'acceleration' ? 'active' : ''}`}
          onClick={() => setActiveTab('acceleration')}
        >
          IMU Vertical Acceleration (Z)
        </button>
      </div>

      {/* Main Signal Chart View */}
      <div className="signal-chart-viewport">
        {isLoadingTimeseries ? (
          <div className="research-loading-state">
            <div className="spinner-subtle" />
            <span>Streaming and downsampling observation packets from server...</span>
          </div>
        ) : !chartData.length ? (
          <div className="research-empty-state">
            <span>No telemetry time series loaded for this session.</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            {activeTab === 'heart_rate' ? (
              <ComposedChart
                data={chartData}
                margin={{ top: 10, right: 15, left: -10, bottom: 0 }}
                onClick={(e) => {
                  if (e?.activePayload?.[0]?.payload?.timestamp && onSelectTimestamp) {
                    onSelectTimestamp(e.activePayload[0].payload.timestamp);
                  }
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" opacity={0.4} />
                <XAxis
                  dataKey="timeMins"
                  unit="m"
                  stroke="var(--text-muted)"
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis
                  yAxisId="hr"
                  domain={[40, 150]}
                  unit=" bpm"
                  stroke="var(--text-muted)"
                  fontSize={11}
                  tickLine={false}
                />
                <YAxis
                  yAxisId="g"
                  orientation="right"
                  domain={[0.5, 5.0]}
                  unit="g"
                  stroke="var(--text-muted)"
                  fontSize={11}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine
                  y={baseHR}
                  yAxisId="hr"
                  stroke="var(--color-normal)"
                  strokeDasharray="4 4"
                  label={{ value: `Base HR (${baseHR})`, fill: 'var(--color-normal)', fontSize: 10, position: 'insideTopLeft' }}
                />
                <ReferenceLine
                  y={1.5}
                  yAxisId="g"
                  stroke="var(--brand-saffron)"
                  strokeDasharray="2 2"
                  opacity={0.6}
                />
                {selectedTimeMins !== null && (
                  <ReferenceLine
                    x={selectedTimeMins}
                    stroke="var(--brand-saffron)"
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    label={{
                      value: `Selected (${selectedTimeMins}m)`,
                      fill: 'var(--brand-saffron)',
                      fontSize: 10,
                      position: 'top',
                    }}
                  />
                )}
                <Line
                  yAxisId="hr"
                  type="monotone"
                  dataKey="heartRate"
                  name="Heart Rate"
                  stroke="var(--text-primary)"
                  strokeWidth={1.8}
                  dot={false}
                  connectNulls={false}
                />
                <Line
                  yAxisId="g"
                  type="monotone"
                  dataKey="gLoad"
                  name="Airframe G-Force"
                  stroke="var(--brand-saffron)"
                  strokeWidth={1.2}
                  dot={false}
                  opacity={0.85}
                />
              </ComposedChart>
            ) : activeTab === 'rr_interval' ? (
              <ComposedChart
                data={chartData}
                margin={{ top: 10, right: 15, left: -10, bottom: 0 }}
                onClick={(e) => {
                  if (e?.activePayload?.[0]?.payload?.timestamp && onSelectTimestamp) {
                    onSelectTimestamp(e.activePayload[0].payload.timestamp);
                  }
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" opacity={0.4} />
                <XAxis dataKey="timeMins" unit="m" stroke="var(--text-muted)" fontSize={11} />
                <YAxis domain={[350, 1300]} unit=" ms" stroke="var(--text-muted)" fontSize={11} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine
                  y={Number((60000.0 / baseHR).toFixed(1))}
                  stroke="var(--color-normal)"
                  strokeDasharray="4 4"
                  label={{ value: `Resting Mean RR (${Number((60000.0 / baseHR).toFixed(0))} ms)`, fill: 'var(--color-normal)', fontSize: 10 }}
                />
                {selectedTimeMins !== null && (
                  <ReferenceLine
                    x={selectedTimeMins}
                    stroke="var(--brand-saffron)"
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    label={{
                      value: `Selected (${selectedTimeMins}m)`,
                      fill: 'var(--brand-saffron)',
                      fontSize: 10,
                      position: 'top',
                    }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="rrInterval"
                  name="RR Interval"
                  stroke="var(--color-cyan)"
                  strokeWidth={1.5}
                  dot={false}
                  connectNulls={false}
                />
              </ComposedChart>
            ) : (
              <ComposedChart
                data={chartData}
                margin={{ top: 10, right: 15, left: -10, bottom: 0 }}
                onClick={(e) => {
                  if (e?.activePayload?.[0]?.payload?.timestamp && onSelectTimestamp) {
                    onSelectTimestamp(e.activePayload[0].payload.timestamp);
                  }
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" opacity={0.4} />
                <XAxis dataKey="timeMins" unit="m" stroke="var(--text-muted)" fontSize={11} />
                <YAxis domain={[0.0, 5.0]} unit="g" stroke="var(--text-muted)" fontSize={11} />
                <Tooltip content={<CustomTooltip />} />
                {selectedTimeMins !== null && (
                  <ReferenceLine
                    x={selectedTimeMins}
                    stroke="var(--brand-saffron)"
                    strokeWidth={2}
                    strokeDasharray="3 3"
                    label={{
                      value: `Selected (${selectedTimeMins}m)`,
                      fill: 'var(--brand-saffron)',
                      fontSize: 10,
                      position: 'top',
                    }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="accelZ"
                  name="Z Acceleration"
                  stroke="var(--brand-green)"
                  strokeWidth={1.4}
                  dot={false}
                />
              </ComposedChart>
            )}
          </ResponsiveContainer>
        )}
      </div>

      {/* Hardware Non-Fabrication Footnote */}
      <div className="non-fabrication-strip">
        <span className="info-icon">ℹ️</span>
        <span>
          <strong>Hardware Non-Fabrication Protocol:</strong> Channels <code>SpO2</code> and <code>Skin Temperature</code> are not continuously acquired by current watch hardware and are strictly preserved as <code>null</code>. Never substituted with zeroes.
        </span>
      </div>
    </div>
  );
}

export default SignalViewer;
