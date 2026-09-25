# ✈️ AeroVital — Pilot Biometrics & Telemetry Intelligence Dashboard

A mission-critical aeromedical flight biometrics and pilot vitality monitoring dashboard built with **React (v18)** and **Vite (v5)**, integrated with the verified **Django REST API** and **AeroVital Core** engine.

---

## 🏗️ Architecture Overview

The React dashboard operates as a **strict presentation layer**. It does not independently evaluate physiological state, calculate fatigue, compute confidence, derive signal quality indices, or establish safety thresholds. All intelligence and validation are performed by the verified AeroVital Core and persisted in the Django backend.

```
React / Vite Dashboard (web/)
         │  HTTPS / Token Auth
         ▼
Django REST API (django-backend/)
         │
         ▼
AeroVital Core Engine & PostgreSQL
```

---

## 🚀 Key Features

* **Real-Time Fatigue & Vitality Monitoring:** Consumes `/api/v1/intelligence/current-state/` displaying verified Core fatigue classifications (`NORMAL`, `ELEVATED_WORKLOAD`, `FATIGUE`, `INSUFFICIENT_DATA`), confidence, SQI, freshness, and dominant contributing factors.
* **Continuous Physiological Telemetry:** Consumes `/api/v1/telemetry/` streaming verified heart rate, blood oxygen (SpO2), HRV (RMSSD/RR intervals), peripheral skin temperature, and motion indicators without fabrication or synthetic noise.
* **State Estimates Timeline:** Plots historical fatigue estimates and confidence levels over flight duration using `/api/v1/intelligence/estimates/`.
* **Aviation Safety Alerts:** Slide-out alert notification drawer consuming `/api/v1/alerts/` with operator acknowledgment support.
* **Pilot & Mission Context:** Authenticated flight deck context scoped to the active pilot and flight mission via `/api/v1/auth/me/` and `/api/v1/missions/`.
* **Cockpit Night HUD Mode:** 1-click toggle between standard high-visibility daylight theme and dark Cockpit Night HUD vision mode.
* **CSV Telemetry Export:** Instant client-side CSV export of verified telemetry packet logs.
* **Simulation Bench:** Explicitly labeled, isolated demo oscilloscope bench for display calibration (non-physiological).

---

## 🛠️ Project Structure

```
web/
├── index.html                 # Vite HTML entry point mounting <div id="root">
├── vite.config.js             # Vite & Vitest configuration
├── package.json               # NPM scripts and dependencies (React, Recharts, Vitest)
├── API_CONTRACT.md            # Comprehensive REST API contracts & mapping
├── src/
│   ├── main.jsx               # React entry point
│   ├── App.jsx                # Application root with AuthProvider & routing
│   ├── setupTests.js          # Vitest testing setup & polyfills
│   ├── components/            # Modular presentation components
│   │   ├── Header.jsx
│   │   ├── StatusBanner.jsx
│   │   ├── CurrentSessionCard.jsx
│   │   ├── CurrentStateCard.jsx
│   │   ├── TelemetryDetails.jsx
│   │   ├── VitalityTimelineChart.jsx
│   │   ├── TelemetryStreamChart.jsx
│   │   ├── AtmosphericStrip.jsx
│   │   ├── TelemetryLogsTable.jsx
│   │   ├── AlertsDrawer.jsx
│   │   ├── PilotProfileModal.jsx
│   │   └── DemoECGPanel.jsx
│   ├── pages/
│   │   ├── DashboardPage.jsx
│   │   └── LoginPage.jsx
│   ├── hooks/
│   │   ├── useAuth.jsx        # Django Token auth state management
│   │   └── useDashboardData.js # Multi-endpoint data polling & status machine
│   ├── services/
│   │   └── api.js             # Standardized HTTP client for Django REST API
│   ├── utils/
│   │   └── formatters.js      # Presentation-only formatters and state configs
│   ├── styles/
│   │   ├── theme.css          # Design tokens, typography, and dark/light themes
│   │   └── dashboard.css      # Component layouts and responsive stylesheets
│   └── __tests__/
│       └── dashboard.test.jsx # Comprehensive frontend test suite
```

---

## ⚙️ Configuration & Environment

Set the backend API base URL using the `VITE_API_BASE_URL` environment variable.

Create a `.env` file in `web/` if pointing to a non-default host:
```env
VITE_API_BASE_URL=http://localhost:8000
```

*(Defaults to `http://localhost:8000` if unspecified).*

---

## 💻 Development & Build Commands

### Install Dependencies
```bash
npm install
```

### Start Local Development Server
```bash
npm run dev
```

### Run Frontend Test Suite
```bash
npm test
```

### Build for Production
```bash
npm run build
```
*(Artifacts generated to `web/dist/` with exit code 0).*
