import React, { useState, useEffect, useRef } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

function App() {
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [telemetry, setTelemetry] = useState(null);
  const [fatigue, setFatigue] = useState(null);
  
  // Historical data for charts
  const [history, setHistory] = useState([]);
  
  // Maximum data points to keep in chart history
  const maxDataPoints = 60; 
  
  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/live');
    
    ws.onopen = () => {
      setConnectionStatus('Connected');
    };
    
    ws.onclose = () => {
      setConnectionStatus('Disconnected');
    };
    
    ws.onerror = (error) => {
      setConnectionStatus('Error');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'update') {
        const { telemetry: t, fatigue: f } = data;
        setTelemetry(t);
        setFatigue(f);
        
        // Add to history
        setHistory(prev => {
          const newPoint = {
            time: new Date(t.timestamp).toLocaleTimeString(),
            hr: t.heart_rate,
            fatigueScore: f.fatigue_score
          };
          const newHistory = [...prev, newPoint];
          if (newHistory.length > maxDataPoints) {
            newHistory.shift();
          }
          return newHistory;
        });
      }
    };
    
    return () => {
      ws.close();
    };
  }, []);
  
  const containerStyle = {
    padding: '20px',
    maxWidth: '1200px',
    margin: '0 auto',
    fontFamily: 'sans-serif'
  };
  
  const cardStyle = {
    background: '#1e1e1e',
    borderRadius: '8px',
    padding: '16px',
    marginBottom: '20px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
  };
  
  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '20px',
    marginBottom: '20px'
  };

  const statBoxStyle = {
    background: '#2c2c2c',
    padding: '15px',
    borderRadius: '6px',
    display: 'flex',
    flexDirection: 'column'
  };

  const labelStyle = {
    fontSize: '0.85rem',
    color: '#aaa',
    marginBottom: '5px'
  };

  const valStyle = {
    fontSize: '1.5rem',
    fontWeight: 'bold',
    color: '#fff'
  };

  return (
    <div style={containerStyle}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>AeroVital Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '12px', height: '12px', borderRadius: '50%',
            backgroundColor: connectionStatus === 'Connected' ? '#4caf50' : '#f44336'
          }}></div>
          <span>{connectionStatus}</span>
        </div>
      </header>
      
      {telemetry && fatigue ? (
        <>
          <div style={gridStyle}>
            {/* Physiology */}
            <div style={statBoxStyle}>
              <span style={labelStyle}>Heart Rate</span>
              <span style={valStyle}>{telemetry.heart_rate} bpm</span>
            </div>
            <div style={statBoxStyle}>
              <span style={labelStyle}>HRV (RMSSD)</span>
              <span style={valStyle}>{telemetry.hrv_rmssd !== null ? telemetry.hrv_rmssd : 'N/A'} ms</span>
            </div>
            <div style={statBoxStyle}>
              <span style={labelStyle}>SpO2</span>
              <span style={valStyle}>{telemetry.spo2 !== null ? `${telemetry.spo2}%` : 'N/A'}</span>
            </div>
            <div style={statBoxStyle}>
              <span style={labelStyle}>Resp. Rate</span>
              <span style={valStyle}>{telemetry.respiratory_rate !== null ? telemetry.respiratory_rate : 'N/A'} rpm</span>
            </div>
            
            {/* Context */}
            <div style={statBoxStyle}>
              <span style={labelStyle}>Mission Phase</span>
              <span style={valStyle}>{telemetry.mission_phase || 'N/A'}</span>
            </div>
            <div style={statBoxStyle}>
              <span style={labelStyle}>G-Load</span>
              <span style={valStyle}>{telemetry.g_load !== null ? `${telemetry.g_load} G` : 'N/A'}</span>
            </div>
            
            {/* Fatigue */}
            <div style={{ ...statBoxStyle, border: `2px solid ${fatigue.fatigue_state === 'NORMAL' ? '#4caf50' : fatigue.fatigue_state === 'ELEVATED_WORKLOAD' ? '#ff9800' : '#f44336'}` }}>
              <span style={labelStyle}>Fatigue State</span>
              <span style={{ ...valStyle, color: fatigue.fatigue_state === 'NORMAL' ? '#4caf50' : fatigue.fatigue_state === 'ELEVATED_WORKLOAD' ? '#ff9800' : '#f44336' }}>
                {fatigue.fatigue_state}
              </span>
            </div>
            <div style={statBoxStyle}>
              <span style={labelStyle}>Fatigue Score / Confidence</span>
              <span style={valStyle}>{(fatigue.fatigue_score).toFixed(2)} / {(fatigue.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>
          
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0, marginBottom: '10px' }}>Dominant Fatigue Factors</h3>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#ffeb3b' }}>
              {fatigue.dominant_factors.length > 0 
                ? fatigue.dominant_factors.map((f, i) => <li key={i}>{f}</li>)
                : <li>None</li>
              }
            </ul>
          </div>
          
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Heart Rate Trend</h3>
            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                  <XAxis dataKey="time" stroke="#aaa" />
                  <YAxis domain={['auto', 'auto']} stroke="#aaa" />
                  <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none' }} />
                  <Legend />
                  <Line type="monotone" dataKey="hr" stroke="#ff7300" dot={false} strokeWidth={2} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>Fatigue Score Trend</h3>
            <div style={{ height: '300px', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                  <XAxis dataKey="time" stroke="#aaa" />
                  <YAxis domain={[0, 1]} stroke="#aaa" />
                  <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none' }} />
                  <Legend />
                  <Line type="monotone" dataKey="fatigueScore" stroke="#4caf50" dot={false} strokeWidth={2} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      ) : (
        <div style={cardStyle}>
          <p>Waiting for telemetry data...</p>
        </div>
      )}
    </div>
  );
}

export default App;
