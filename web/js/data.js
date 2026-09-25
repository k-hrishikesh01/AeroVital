/**
 * AeroVital Dashboard - Biometric Telemetry & State Management Data
 * Pure Front-End Data Store (No backend required)
 */

const INITIAL_DATA = {
  // Primary Session Metrics matching screenshot
  session: {
    hours: 2,
    minutes: 45,
    seconds: 32,
    totalSeconds: 2 * 3600 + 45 * 60 + 32, // 02:45:32
    isRunning: true,
    flightNo: 'AV-409',
    route: 'DXB ➔ LHR',
    aircraft: 'Boeing 787-9 Dreamliner',
    cruisingAlt: '37,000 FT',
    cabinAlt: '6,100 FT',
    speed: '492 KTS'
  },
  vitals: {
    sScore: 78,
    conference: 50, // Matches screenshot label "Conference"
    condition: 'NORMAL',
    conditionDetails: 'All bio-markers optimal. Alertness within peak threshold.',
    lastEstimated: 'Last estimated 2 minutes ago',
    heartRate: 78,
    heartRateUnit: 'BPM',
    fatigueState: 'Low',
    lastSession: 'Today',
    spo2: 98.4, // %
    respirationRate: 15, // Breaths/min
    bodyTemp: 36.7, // °C
    perclos: 3.2, // % eye closure
    reactionTime: 218, // ms
    cognitiveLoad: 42, // %
    stressIndex: 22, // /100
    gForce: 1.02 // G
  },
  activePilot: {
    name: 'Capt. Sarah Jenkins',
    id: 'AV-8821',
    role: 'Captain / PIC',
    aircraftRating: 'B787 / A350',
    flightHours: '8,420 hrs',
    status: 'On Duty (Cruising Phase)',
    avatar: 'SJ'
  },
  pilotsList: [
    {
      name: 'Capt. Sarah Jenkins',
      id: 'AV-8821',
      role: 'Captain / PIC',
      aircraftRating: 'B787 / A350',
      flightHours: '8,420 hrs',
      avatar: 'SJ'
    },
    {
      name: 'F/O Marcus Vance',
      id: 'AV-9042',
      role: 'First Officer / SIC',
      aircraftRating: 'B787-9',
      flightHours: '3,850 hrs',
      avatar: 'MV'
    },
    {
      name: 'F/O Elena Rostova',
      id: 'AV-9130',
      role: 'Relief Cruise Pilot',
      aircraftRating: 'B787 / B777',
      flightHours: '2,640 hrs',
      avatar: 'ER'
    }
  ],
  // Historical telemetry log entries for session
  historicalLogs: [
    { time: '00:00', phase: 'Pre-Flight Briefing', hr: 72, sScore: 88, fatigue: 'Low', status: 'Normal' },
    { time: '00:30', phase: 'Taxi & Takeoff Climb', hr: 89, sScore: 75, fatigue: 'Low', status: 'Normal' },
    { time: '01:00', phase: 'Level Off FL350', hr: 79, sScore: 82, fatigue: 'Low', status: 'Normal' },
    { time: '01:30', phase: 'En-route Cruise', hr: 76, sScore: 80, fatigue: 'Low', status: 'Normal' },
    { time: '02:00', phase: 'Minor Turbulence (FL370)', hr: 84, sScore: 74, fatigue: 'Low', status: 'Normal' },
    { time: '02:30', phase: 'Steady Cruise', hr: 77, sScore: 78, fatigue: 'Low', status: 'Normal' },
    { time: '02:45', phase: 'Current Session Time', hr: 78, sScore: 78, fatigue: 'Low', status: 'Normal' }
  ],
  // Radar data: 6 Cognitive & Physical Pillars
  radarMetrics: {
    labels: ['Alertness', 'Reaction Speed', 'Cardiac Stability', 'Hypoxia Tolerance', 'Cognitive Focus', 'Stress Buffer'],
    current: [88, 82, 92, 85, 78, 84],
    baseline: [90, 85, 90, 85, 85, 80]
  },
  // Circadian rhythm forecast
  circadianForecast: {
    hours: ['14:00', '15:00', '16:00', '17:00 (Now)', '18:00', '19:00', '20:00', '21:00 (Descent)', '22:00 (Landing)'],
    alertnessScore: [90, 87, 83, 78, 76, 73, 69, 82, 85],
    fatigueRisk: [10, 12, 18, 22, 26, 31, 38, 28, 20]
  },
  alerts: [
    { id: 1, type: 'info', time: '10 min ago', title: 'Cruising Altitude Reached', desc: 'Cabin pressure normalized at 6,100 FT equivalent.' },
    { id: 2, type: 'success', time: '2 min ago', title: 'Biometric Telemetry Synchronized', desc: 'PPG & ECG sensor confidence calibrated at 98% fidelity.' },
    { id: 3, type: 'notice', time: 'Just now', title: 'Hydration & Rest Interval', desc: 'Next recommended cockpit relief swap scheduled in 45 mins.' }
  ]
};

// Global export for pure front-end usage
if (typeof window !== 'undefined') {
  window.INITIAL_DATA = INITIAL_DATA;
}
