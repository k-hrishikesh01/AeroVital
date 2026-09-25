/**
 * AeroVital Dashboard - Chart.js Visualizations
 * Pure Front-End Interactive Charts
 */

class DashboardCharts {
  constructor() {
    this.timelineChart = null;
    this.streamChart = null;
    this.radarChart = null;
    this.circadianChart = null;
    this.streamInterval = null;
    this.isStreaming = true;
    
    // Check if Chart.js is loaded
    if (typeof Chart === 'undefined') {
      console.error('Chart.js is not loaded.');
      return;
    }

    this.setupChartDefaults();
    this.initVitalityTimeline();
    this.initRealtimeStream();
    this.initReadinessRadar();
    this.initCircadianForecast();
  }

  isDark() {
    return document.body.classList.contains('dark-theme');
  }

  getColors() {
    const dark = this.isDark();
    return {
      textColor: dark ? '#94A3B8' : '#64748B',
      titleColor: dark ? '#F8FAFC' : '#0F172A',
      gridColor: dark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)',
      navy: '#19375F',
      emerald: '#10B981',
      emeraldLight: 'rgba(16, 185, 129, 0.15)',
      amber: '#F59E0B',
      amberLight: 'rgba(245, 158, 11, 0.15)',
      cyan: '#0EA5E9',
      cyanLight: 'rgba(14, 165, 233, 0.15)',
      purple: '#8B5CF6',
      purpleLight: 'rgba(139, 92, 246, 0.15)',
      cardBg: dark ? '#111827' : '#FFFFFF'
    };
  }

  setupChartDefaults() {
    const colors = this.getColors();
    Chart.defaults.font.family = "'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif";
    Chart.defaults.color = colors.textColor;
    Chart.defaults.plugins.tooltip.backgroundColor = colors.isDark ? '#1E293B' : '#0F172A';
    Chart.defaults.plugins.tooltip.titleColor = '#F8FAFC';
    Chart.defaults.plugins.tooltip.bodyColor = '#CBD5E1';
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
    Chart.defaults.plugins.tooltip.padding = 12;
  }

  // 1. Vitality Timeline (S-Score, Heart Rate, Fatigue %)
  initVitalityTimeline() {
    const canvas = document.getElementById('timelineChart');
    if (!canvas) return;

    const colors = this.getColors();
    const ctx = canvas.getContext('2d');

    // Create subtle gradient for S-Score
    const gradientS = ctx.createLinearGradient(0, 0, 0, 280);
    gradientS.addColorStop(0, 'rgba(16, 185, 129, 0.28)');
    gradientS.addColorStop(1, 'rgba(16, 185, 129, 0.01)');

    const gradientHR = ctx.createLinearGradient(0, 0, 0, 280);
    gradientHR.addColorStop(0, 'rgba(14, 165, 233, 0.20)');
    gradientHR.addColorStop(1, 'rgba(14, 165, 233, 0.01)');

    const labels = ['00:00', '00:20', '00:40', '01:00', '01:20', '01:40', '02:00', '02:20', '02:40', '02:45 (Now)'];
    const sScoreData = [88, 86, 80, 82, 84, 81, 75, 76, 79, 78];
    const hrData = [72, 79, 86, 80, 77, 75, 83, 76, 77, 78];
    const fatigueData = [8, 12, 16, 18, 19, 21, 25, 24, 22, 21];

    this.timelineChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'S-Score (%)',
            data: sScoreData,
            borderColor: colors.emerald,
            backgroundColor: gradientS,
            borderWidth: 2.5,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: colors.emerald,
            pointBorderColor: '#FFFFFF',
            pointRadius: 4,
            pointHoverRadius: 6,
            yAxisID: 'y'
          },
          {
            label: 'Heart Rate (BPM)',
            data: hrData,
            borderColor: colors.cyan,
            backgroundColor: gradientHR,
            borderWidth: 2,
            borderDash: [4, 4],
            fill: false,
            tension: 0.3,
            pointBackgroundColor: colors.cyan,
            pointRadius: 3,
            pointHoverRadius: 5,
            yAxisID: 'y1'
          },
          {
            label: 'Fatigue Risk (%)',
            data: fatigueData,
            borderColor: colors.amber,
            borderWidth: 2,
            fill: false,
            tension: 0.3,
            pointBackgroundColor: colors.amber,
            pointRadius: 3,
            pointHoverRadius: 5,
            yAxisID: 'y'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
            labels: {
              boxWidth: 12,
              boxHeight: 12,
              usePointStyle: true,
              font: { weight: 600, size: 12 }
            }
          }
        },
        scales: {
          x: {
            grid: { color: colors.gridColor },
            ticks: { font: { size: 11 } }
          },
          y: {
            type: 'linear',
            position: 'left',
            min: 0,
            max: 100,
            grid: { color: colors.gridColor },
            ticks: {
              callback: (val) => val + '%',
              stepSize: 20
            },
            title: {
              display: true,
              text: 'S-Score & Fatigue (%)',
              font: { size: 11, weight: 600 }
            }
          },
          y1: {
            type: 'linear',
            position: 'right',
            min: 50,
            max: 120,
            grid: { drawOnChartArea: false },
            ticks: {
              callback: (val) => val + ' bpm',
              stepSize: 15
            },
            title: {
              display: true,
              text: 'Heart Rate (BPM)',
              font: { size: 11, weight: 600 }
            }
          }
        }
      }
    });
  }

  // 2. Real-time Rolling Stream (Rolling 20-point live window)
  initRealtimeStream() {
    const canvas = document.getElementById('realtimeStreamChart');
    if (!canvas) return;

    const colors = this.getColors();
    const ctx = canvas.getContext('2d');

    const maxPoints = 20;
    const initialLabels = [];
    const initialHR = [];
    const initialHRV = [];
    
    let baseTime = new Date();
    for (let i = maxPoints; i > 0; i--) {
      const t = new Date(baseTime.getTime() - i * 2000);
      initialLabels.push(t.toTimeString().split(' ')[0]);
      initialHR.push(77 + Math.sin(i) * 2 + (Math.random() * 2 - 1));
      initialHRV.push(54 + Math.cos(i) * 3 + (Math.random() * 2 - 1));
    }

    this.streamChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: initialLabels,
        datasets: [
          {
            label: 'Heart Rate (BPM)',
            data: initialHR,
            borderColor: '#EF4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: 2,
            pointHoverRadius: 5
          },
          {
            label: 'HRV (ms)',
            data: initialHRV,
            borderColor: '#3B82F6',
            borderWidth: 1.8,
            tension: 0.3,
            borderDash: [3, 3],
            fill: false,
            pointRadius: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        scales: {
          x: {
            grid: { color: colors.gridColor },
            ticks: { maxTicksLimit: 6, font: { size: 10 } }
          },
          y: {
            min: 40,
            max: 110,
            grid: { color: colors.gridColor },
            ticks: { stepSize: 15 }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { boxWidth: 10, usePointStyle: true, font: { size: 11 } }
          }
        }
      }
    });

    this.startStreaming();
  }

  startStreaming() {
    if (this.streamInterval) clearInterval(this.streamInterval);
    this.streamInterval = setInterval(() => {
      if (!this.isStreaming || !this.streamChart) return;

      const now = new Date();
      const timeStr = now.toTimeString().split(' ')[0];

      // Get current base heart rate from state
      const currentBpm = window.AeroVitalState?.vitals?.heartRate || 78;
      const noise = (Math.random() * 3 - 1.5);
      const newBpm = Math.round(currentBpm + noise);
      const newHRV = Math.round(55 + (Math.random() * 6 - 3));

      const labels = this.streamChart.data.labels;
      const hrData = this.streamChart.data.datasets[0].data;
      const hrvData = this.streamChart.data.datasets[1].data;

      labels.shift();
      labels.push(timeStr);

      hrData.shift();
      hrData.push(newBpm);

      hrvData.shift();
      hrvData.push(newHRV);

      this.streamChart.update('none');
    }, 2000);
  }

  // 3. Cognitive & Readiness Radar Chart
  initReadinessRadar() {
    const canvas = document.getElementById('readinessRadarChart');
    if (!canvas) return;

    const colors = this.getColors();
    const ctx = canvas.getContext('2d');
    const { labels, current, baseline } = (window.INITIAL_DATA || {}).radarMetrics || {
      labels: ['Alertness', 'Reaction Speed', 'Cardiac Stability', 'Hypoxia Tolerance', 'Cognitive Focus', 'Stress Buffer'],
      current: [88, 82, 92, 85, 78, 84],
      baseline: [90, 85, 90, 85, 85, 80]
    };

    this.radarChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Current State',
            data: current,
            backgroundColor: 'rgba(16, 185, 129, 0.2)',
            borderColor: colors.emerald,
            borderWidth: 2,
            pointBackgroundColor: colors.emerald,
            pointRadius: 3
          },
          {
            label: 'Baseline Standard',
            data: baseline,
            backgroundColor: 'rgba(100, 116, 139, 0.1)',
            borderColor: '#64748B',
            borderWidth: 1.5,
            borderDash: [4, 4],
            pointBackgroundColor: '#64748B',
            pointRadius: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 10, usePointStyle: true, font: { size: 11 } }
          }
        },
        scales: {
          r: {
            min: 50,
            max: 100,
            ticks: { display: false, stepSize: 10 },
            grid: { color: colors.gridColor },
            angleLines: { color: colors.gridColor },
            pointLabels: {
              font: { size: 11, weight: 600 },
              color: colors.textColor
            }
          }
        }
      }
    });
  }

  // 4. Circadian Rhythm & Sleep Debt Forecast
  initCircadianForecast() {
    const canvas = document.getElementById('circadianChart');
    if (!canvas) return;

    const colors = this.getColors();
    const ctx = canvas.getContext('2d');
    const { hours, alertnessScore, fatigueRisk } = (window.INITIAL_DATA || {}).circadianForecast || {
      hours: ['14:00', '15:00', '16:00', '17:00 (Now)', '18:00', '19:00', '20:00', '21:00 (Descent)', '22:00 (Landing)'],
      alertnessScore: [90, 87, 83, 78, 76, 73, 69, 82, 85],
      fatigueRisk: [10, 12, 18, 22, 26, 31, 38, 28, 20]
    };

    this.circadianChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: hours,
        datasets: [
          {
            type: 'line',
            label: 'Predicted Alertness',
            data: alertnessScore,
            borderColor: colors.cyan,
            backgroundColor: colors.cyan,
            borderWidth: 2.5,
            tension: 0.35,
            fill: false,
            yAxisID: 'y'
          },
          {
            type: 'bar',
            label: 'Fatigue Accumulation Risk',
            data: fatigueRisk,
            backgroundColor: fatigueRisk.map(v => v > 30 ? 'rgba(239, 68, 68, 0.65)' : (v > 20 ? 'rgba(245, 158, 11, 0.6)' : 'rgba(16, 185, 129, 0.5)')),
            borderRadius: 6,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { boxWidth: 10, usePointStyle: true, font: { size: 11 } }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 10 } }
          },
          y: {
            min: 40,
            max: 100,
            position: 'left',
            grid: { color: colors.gridColor },
            title: { display: true, text: 'Alertness Index' }
          },
          y1: {
            min: 0,
            max: 60,
            position: 'right',
            grid: { display: false },
            title: { display: true, text: 'Fatigue Risk %' }
          }
        }
      }
    });
  }

  updateFilterRange(range) {
    if (!this.timelineChart) return;

    let newLabels = [];
    let newS = [];
    let newHR = [];
    let newFatigue = [];

    if (range === '30m') {
      newLabels = ['02:15', '02:20', '02:25', '02:30', '02:35', '02:40', '02:45'];
      newS = [76, 76, 77, 78, 77, 79, 78];
      newHR = [75, 76, 77, 77, 78, 77, 78];
      newFatigue = [23, 23, 22, 22, 22, 21, 21];
    } else if (range === '1h') {
      newLabels = ['01:45', '01:55', '02:05', '02:15', '02:25', '02:35', '02:45'];
      newS = [81, 79, 75, 76, 77, 78, 78];
      newHR = [75, 78, 83, 76, 77, 78, 78];
      newFatigue = [20, 22, 25, 23, 22, 21, 21];
    } else {
      newLabels = ['00:00', '00:20', '00:40', '01:00', '01:20', '01:40', '02:00', '02:20', '02:40', '02:45'];
      newS = [88, 86, 80, 82, 84, 81, 75, 76, 79, 78];
      newHR = [72, 79, 86, 80, 77, 75, 83, 76, 77, 78];
      newFatigue = [8, 12, 16, 18, 19, 21, 25, 24, 22, 21];
    }

    this.timelineChart.data.labels = newLabels;
    this.timelineChart.data.datasets[0].data = newS;
    this.timelineChart.data.datasets[1].data = newHR;
    this.timelineChart.data.datasets[2].data = newFatigue;
    this.timelineChart.update();
  }

  updateConditionState(condition, sScore, hr) {
    if (!this.timelineChart) return;
    const len = this.timelineChart.data.datasets[0].data.length;
    this.timelineChart.data.datasets[0].data[len - 1] = sScore;
    this.timelineChart.data.datasets[1].data[len - 1] = hr;
    this.timelineChart.update('none');

    if (this.radarChart) {
      if (condition === 'WARNING' || condition === 'FATIGUE') {
        this.radarChart.data.datasets[0].data = [65, 68, 74, 80, 62, 60];
      } else {
        this.radarChart.data.datasets[0].data = [88, 82, 92, 85, 78, 84];
      }
      this.radarChart.update();
    }
  }

  updateTheme() {
    const colors = this.getColors();
    const updateScales = (chart) => {
      if (!chart) return;
      if (chart.options.scales) {
        Object.keys(chart.options.scales).forEach(key => {
          const scale = chart.options.scales[key];
          if (scale.grid) scale.grid.color = colors.gridColor;
          if (scale.ticks) scale.ticks.color = colors.textColor;
        });
      }
      chart.update();
    };

    updateScales(this.timelineChart);
    updateScales(this.streamChart);
    updateScales(this.circadianChart);

    if (this.radarChart) {
      this.radarChart.options.scales.r.grid.color = colors.gridColor;
      this.radarChart.options.scales.r.angleLines.color = colors.gridColor;
      this.radarChart.options.scales.r.pointLabels.color = colors.textColor;
      this.radarChart.update();
    }
  }
}

// Global export for pure front-end
if (typeof window !== 'undefined') {
  window.DashboardCharts = DashboardCharts;
}
