/**
 * Demo / Simulation Oscilloscope
 *
 * CRITICAL ARCHITECTURE RULE (Requirement 15):
 * This component is an explicit DEMO / SIMULATION ONLY.
 * It is NOT live pilot ECG telemetry.
 */

import React, { useRef, useEffect, useState } from 'react';

export function DemoECGPanel({ currentBpm = 75 }) {
  const canvasRef = useRef(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (!isExpanded) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let phase = 0;
    const maxPoints = 250;
    const points = new Array(maxPoints).fill(0);

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = (rect.width || 300) * dpr;
      canvas.height = (rect.height || 60) * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();

    const getECGValue = (t) => {
      if (t > 0.12 && t < 0.22) {
        const p = (t - 0.17) / 0.05;
        return Math.exp(-p * p * 8) * 0.18;
      } else if (t >= 0.32 && t < 0.35) {
        return -0.15 * Math.sin(((t - 0.32) / 0.03) * Math.PI);
      } else if (t >= 0.35 && t < 0.41) {
        const r = (t - 0.38) / 0.03;
        return Math.exp(-r * r * 16) * 1.0;
      } else if (t >= 0.41 && t < 0.46) {
        const s = (t - 0.435) / 0.025;
        return -0.32 * Math.exp(-s * s * 14);
      } else if (t >= 0.58 && t < 0.78) {
        const tw = (t - 0.68) / 0.1;
        return Math.exp(-tw * tw * 8) * 0.32;
      }
      return Math.sin(t * Math.PI * 18) * 0.02;
    };

    const draw = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width || 300;
      const h = rect.height || 60;
      const midY = h * 0.55;
      const amplitude = h * 0.42;

      const beatsPerSec = (currentBpm || 75) / 60;
      phase = (phase + beatsPerSec / 60) % 1.0;
      points.shift();
      points.push(getECGValue(phase));

      ctx.clearRect(0, 0, w, h);

      // Grid
      ctx.save();
      ctx.strokeStyle = 'rgba(100, 116, 139, 0.1)';
      ctx.lineWidth = 1;
      for (let x = 0; x < w; x += 15) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      ctx.restore();

      // Waveform
      ctx.save();
      ctx.strokeStyle = '#10B981';
      ctx.lineWidth = 2;
      ctx.beginPath();
      const dx = w / (points.length - 1);
      for (let i = 0; i < points.length; i++) {
        const x = i * dx;
        const y = midY - (points[i] * amplitude);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.restore();

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, [isExpanded, currentBpm]);

  return (
    <article className="chart-card" style={{ border: '1px dashed var(--color-warning)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <span style={{
            fontSize: '10px',
            fontWeight: 800,
            textTransform: 'uppercase',
            padding: '2px 8px',
            borderRadius: '4px',
            backgroundColor: 'var(--color-warning-bg)',
            color: 'var(--color-warning)',
            marginRight: '8px'
          }}>
            SIMULATION ONLY
          </span>
          <strong style={{ fontSize: '13px' }}>Lead-II ECG Oscilloscope Simulator</strong>
        </div>

        <button
          className="btn-secondary"
          style={{ padding: '4px 10px', fontSize: '12px' }}
          onClick={() => setIsExpanded(prev => !prev)}
        >
          {isExpanded ? 'Hide Simulation' : 'Show Simulation Bench'}
        </button>
      </div>

      {isExpanded && (
        <div style={{ marginTop: '14px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            Notice: Raw Lead-II ECG requires 250Hz hardware stream ingestion. The visualizer below is a synthetic mathematical P-Q-R-S-T model for display calibration only.
          </div>
          <div style={{ height: '70px', background: 'var(--bg-card-tinted)', borderRadius: '10px', overflow: 'hidden' }}>
            <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }}></canvas>
          </div>
        </div>
      )}
    </article>
  );
}

export default DemoECGPanel;
