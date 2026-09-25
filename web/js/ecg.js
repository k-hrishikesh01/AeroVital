/**
 * Live Canvas ECG Waveform Generator
 * Pure Front-End Medical-grade P-Q-R-S-T electrocardiogram oscilloscope
 */

class ECGMonitor {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.bpm = 78;
    this.phase = 0;
    this.points = [];
    this.maxPoints = 250;
    this.animationFrame = null;
    this.color = '#10B981'; // default emerald / cyan
    this.glowColor = 'rgba(16, 185, 129, 0.4)';

    this.resize();
    window.addEventListener('resize', () => this.resize());
    this.initPoints();
    this.start();
  }

  resize() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = (rect.width || 300) * dpr;
    this.canvas.height = (rect.height || 60) * dpr;
    this.ctx.scale(dpr, dpr);
    this.width = rect.width || 300;
    this.height = rect.height || 60;
  }

  setBPM(bpm, status = 'NORMAL') {
    this.bpm = bpm;
    if (status === 'NORMAL') {
      this.color = '#10B981';
      this.glowColor = 'rgba(16, 185, 129, 0.4)';
    } else if (status === 'WARNING') {
      this.color = '#F59E0B';
      this.glowColor = 'rgba(245, 158, 11, 0.4)';
    } else {
      this.color = '#EF4444';
      this.glowColor = 'rgba(239, 68, 68, 0.4)';
    }
  }

  initPoints() {
    this.points = [];
    for (let i = 0; i < this.maxPoints; i++) {
      this.points.push(0);
    }
  }

  // Calculate synthetic ECG value at normalized phase t (0 to 1)
  getECGValue(t) {
    if (t > 0.12 && t < 0.22) {
      // P wave
      const p = (t - 0.17) / 0.05;
      return Math.exp(-p * p * 8) * 0.18;
    } else if (t >= 0.32 && t < 0.35) {
      // Q wave (small downward dip)
      return -0.15 * Math.sin(((t - 0.32) / 0.03) * Math.PI);
    } else if (t >= 0.35 && t < 0.41) {
      // R spike (tall upward peak)
      const r = (t - 0.38) / 0.03;
      return Math.exp(-r * r * 16) * 1.0;
    } else if (t >= 0.41 && t < 0.46) {
      // S wave (deep downward plunge)
      const s = (t - 0.435) / 0.025;
      return -0.32 * Math.exp(-s * s * 14);
    } else if (t >= 0.58 && t < 0.78) {
      // T wave (smooth repolarization dome)
      const tw = (t - 0.68) / 0.1;
      return Math.exp(-tw * tw * 8) * 0.32;
    }
    // Baseline micro-fluctuation
    return (Math.sin(t * Math.PI * 18) * 0.02);
  }

  update() {
    // speed based on BPM: 78 bpm = ~1.3 beats/sec
    const beatsPerSec = this.bpm / 60;
    const delta = (beatsPerSec / 60); // assumes ~60fps
    this.phase = (this.phase + delta) % 1.0;

    const val = this.getECGValue(this.phase);
    this.points.shift();
    this.points.push(val);
  }

  draw() {
    if (!this.ctx || !this.canvas) return;
    const w = this.width;
    const h = this.height;
    const midY = h * 0.55;
    const amplitude = h * 0.42;

    this.ctx.clearRect(0, 0, w, h);

    // Draw background grid lines (subtle medical grid)
    this.ctx.save();
    this.ctx.strokeStyle = document.body.classList.contains('dark-theme') 
      ? 'rgba(255, 255, 255, 0.04)' 
      : 'rgba(0, 0, 0, 0.04)';
    this.ctx.lineWidth = 1;
    const step = 15;
    for (let x = 0; x < w; x += step) {
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, h);
      this.ctx.stroke();
    }
    for (let y = 0; y < h; y += step) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(w, y);
      this.ctx.stroke();
    }
    this.ctx.restore();

    // Draw ECG trace
    this.ctx.save();
    this.ctx.strokeStyle = this.color;
    this.ctx.lineWidth = 2.2;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
    this.ctx.shadowColor = this.glowColor;
    this.ctx.shadowBlur = 8;

    this.ctx.beginPath();
    const dx = w / (this.points.length - 1);
    for (let i = 0; i < this.points.length; i++) {
      const x = i * dx;
      const y = midY - (this.points[i] * amplitude);
      if (i === 0) {
        this.ctx.moveTo(x, y);
      } else {
        this.ctx.lineTo(x, y);
      }
    }
    this.ctx.stroke();

    // Draw leading sweep dot
    const headX = (this.points.length - 1) * dx;
    const headY = midY - (this.points[this.points.length - 1] * amplitude);
    this.ctx.beginPath();
    this.ctx.arc(headX, headY, 3.5, 0, Math.PI * 2);
    this.ctx.fillStyle = '#FFFFFF';
    this.ctx.shadowColor = this.color;
    this.ctx.shadowBlur = 12;
    this.ctx.fill();

    this.ctx.restore();
  }

  loop() {
    this.update();
    this.draw();
    this.animationFrame = requestAnimationFrame(() => this.loop());
  }

  start() {
    if (!this.animationFrame) {
      this.loop();
    }
  }

  stop() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }
}

// Global export for pure front-end
if (typeof window !== 'undefined') {
  window.ECGMonitor = ECGMonitor;
}
