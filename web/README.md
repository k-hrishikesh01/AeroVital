# ✈️ AEROVITAL — Pilot Biometrics & Vitality Intelligence Dashboard
### Pure Front-End Web Application (100% Client-Side • Zero Backend Required)

> **AeroVital** is a mission-critical, aeromedical telemetry and flight deck vitality monitoring dashboard designed for commercial pilots, flight surgeons, and airline safety operations.
>
> Built entirely in **pure HTML5, Vanilla CSS3, and modern Vanilla JavaScript**. It has **no backend, no server, and no build dependencies**—it works instantly by double-clicking `index.html` or deploying directly to GitHub Pages / Netlify / Vercel.

---

## 🎨 Color Theme & Design Palette (From Provided Specifications)

The visual design system directly implements the color scheme and layout provided in the project reference mockups:

| Token | Hex Code / Value | Usage & Visual Role | Reference |
| :--- | :--- | :--- | :--- |
| **App Canvas Surface** | `#F4F5F9` | Ultra-clean, cool slate-tinted background | Screen 1 Background |
| **Primary Elevation Card** | `#FFFFFF` | Crisp white elevated card for primary **Session Time** | Screen 1 "Session Time" |
| **Tinted Telemetry Cards** | `#ECEEF4` | Soft cool lavender-tinted surfaces for **S-Score**, **Conference**, & **Condition** | Screen 1 Cards |
| **Aviation Deep Navy** | `#19375F` | Primary button background | Screen 2 "CREATE ACCOUNT" |
| **Status Normal / Optimal**| `#10B981` | Emerald badge and live heartbeat pulse for **NORMAL** condition | Screen 1 "NORMAL" |
| **Warning / Caution** | `#F59E0B` | Amber alert for turbulence stress spikes | Built-in Telemetry |
| **Critical / High Fatigue** | `#EF4444` | Crimson indicator for fatigue advisories & micro-sleep risk | Built-in Telemetry |
| **Cockpit Night Mode** | `#0A0F1D` | High-contrast night vision HUD theme for dark flight decks | Built-in 1-Click Toggle |

---

## 🚀 Key Front-End Features

### 1. ⏱️ Current Session Telemetry (Image 1 Exact Replication)
- **Real-Time Session Stopwatch**: Starts at `02:45:32` (from reference image) and ticks every second, with interactive pause, resume, and reset controls.
- **S-Score Display**: Monitored at `78%` with upward delta trends (`+2.4% Optimal`).
- **Conference / Sensor Confidence**: Live sensor fidelity tracking calibrated at `50%`.
- **Current Condition**: `NORMAL` status badge with dynamic estimation timestamp (`Last estimated 2 minutes ago`).
- **Details Section**:
  - **Heart Rate**: `78 BPM` with rhythmic beating animation.
  - **Fatigue State**: `Low` (tracked via PERCLOS eye closure index).
  - **Last Session**: `Today` history tracking.
  - **SpO2 Oxygen Saturation**: `98.4%` (cabin altitude compensated).
  - **Respiration Rate**: `15 bpm` sinus rhythm.
  - **Cognitive Workload**: `42% (Optimal)`.

### 2. 📊 Rich Interactive Charts & Telemetry Stream
- **Live Sinus Rhythm Oscilloscope**: High-performance HTML5 Canvas rendering a real-time Lead-II P-Q-R-S-T medical electrocardiogram wave synchronized with the pilot's BPM.
- **Flight Vitality Timeline**: Multi-axis Chart.js visualization plotting S-Score, Heart Rate, and Fatigue Risk with interactive time range filtering (**30 Min**, **1 Hour**, **Full Session**).
- **1 Hz Rolling Telemetry Stream**: Continuous 20-point rolling live window graphing BPM and Heart Rate Variability (HRV ms).
- **Aeromedical Readiness Radar**: 6-axis spider chart comparing current cognitive/physical pillars against aeromedical standards (Alertness, Reaction Speed, Cardiac Stability, Hypoxia Tolerance, Focus, Stress Buffer).
- **Circadian Rhythm & Sleep Debt Forecast**: Hourly fatigue accumulation risk predictive model aligned with FAA Part 117 flight duty limitations.

### 3. 👤 Pilot Account Management (Image 2 Exact Replication)
- **Create Pilot Account Dialog**: Pixel-perfect implementation of reference Image 2:
  - `Pilot Name`
  - `Pilot ID`
  - `Password`
  - Deep Navy Blue `CREATE ACCOUNT` button (`#19375F`)
  - `Back to Login` toggle
- **Active Crew Roster**: Instant switching between active Captains, First Officers, and relief pilots with persistent `localStorage` support.

### 4. 🕹️ Telemetry Simulation Presets
Test how the entire dashboard responds to real-world flight scenarios in 1 click:
- **Normal Cruise (Baseline)**: Restores the exact conditions from screenshot 1 (`78 BPM`, `78% S-Score`, `NORMAL`).
- **Turbulence / Stress Spike**: Simulates CAT turbulence, raising HR to `104 BPM` with amber warnings.
- **Fatigue Advisory Alert**: Simulates prolonged micro-fixations, dropping HR to `61 BPM` with critical red relief alerts.

### 5. 🌙 Cockpit Night Vision Mode & Mobile View
- Instant toggle between the crisp **AeroVital Light Theme** and the **Cockpit Night HUD Mode** for night flights.
- **Mobile View Toggle**: Switches between the expanded Flight Operations Center and an authentic mobile phone layout matching Image 1.

### 6. 📁 Telemetry Log Export
- One-click CSV export of historical biometric snapshots recorded during the flight.

---

## 🛠️ Project Structure (Pure Front-End)

```
dashboard/
├── index.html              # Semantic HTML5 dashboard structure
├── css/
│   └── styles.css          # Vanilla CSS design system (Light & Cockpit Night themes)
├── js/
│   ├── app.js              # Application controller & event bindings
│   ├── charts.js           # Interactive Chart.js visualizers
│   ├── ecg.js              # Canvas real-time ECG oscilloscope engine
│   └── data.js             # Initial state, pilots roster & chart data
├── vendor/
│   └── chart.umd.min.js    # Bundled offline Chart.js library (no external CDN needed)
├── .gitignore              # Standard git exclusion rules
└── README.md               # Project documentation & push guide
```

---

## 💻 How to Run (100% Client-Side)

### Option 1: Double-Click `index.html`
Simply double-click `index.html` in your file manager to open it in any web browser (Chrome, Edge, Firefox, Safari).

### Option 2: Deploy to GitHub Pages / Static Host
1. Push this repository to GitHub.
2. In your repo settings, enable **GitHub Pages** (Source: `main` branch, `/root`).
3. Your live dashboard is immediately hosted worldwide with HTTPS for free!

---

## 📦 How to Push to Your Git Repository

When you are ready with your Git repository URL:

```bash
# 1. Add your remote repository URL:
git remote add origin <YOUR_GIT_REPO_URL>

# 2. Push to the main branch:
git push -u origin main
```

*(All project files are already tracked, initialized, and committed on the `main` branch ready for immediate pushing).*
