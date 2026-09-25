# AeroVital

> **Aviation Biometrics & Pilot Fatigue Intelligence System**  
> Operational flight monitoring, multi-channel physiological telemetry, autonomic fatigue detection, and real-time situational awareness.

---

## Project Overview

AeroVital is an aeromedical physiological monitoring and fatigue intelligence platform designed for high-stress aviation and aerospace environments. High-performance flight demands continuous physical and cognitive readiness; acute workload spikes, sustained high-G maneuvers, hypoxia, and prolonged mission sorties impose severe physiological strain on flight crews. 

AeroVital ingests multi-channel physiological sensor streams (ECG, PPG, RR intervals, SpO2, skin temperature, 3-axis accelerometer data), pairs them with real-time operational flight context (maneuver phase, G-load), and evaluates autonomic vitality against calibrated pilot-specific baselines. Rather than relying on black-box opacity or simplistic thresholds, AeroVital features a deterministic, mathematically rigorous Core Engine that explicitly computes signal quality, isolates workload from fatigue, quantifies estimation confidence, and abstains when evidence is insufficient.

---

## Problem Statement

Pilot fatigue and cognitive overload remain leading contributors to flight incidents and spatial disorientation in military and commercial aviation:
- **Workload vs. Fatigue Conflation:** Existing wearables often misclassify high acute operational workload (e.g. combat maneuvering or approach) as fatigue due to elevated heart rates. AeroVital differentiates physiological activation caused by high G-load or demanding flight phases from autonomic fatigue.
- **Inter-Individual Physiological Variability:** Fixed population thresholds fail in aviation. A resting heart rate of 75 BPM or an RMSSD of 30 ms may represent acute fatigue for one pilot while being nominal baseline physiology for another. AeroVital evaluates all metrics against pre-calibrated individual pilot profiles.
- **Sensor Motion Contamination:** High vibration and maneuvering induce significant motion artifacts in optical PPG and ECG sensors. AeroVital screens multi-channel Signal Quality Indices (SQI) before downstream inference, ensuring corrupted data never fabricates false fatigue states.
- **Safety-Critical Decision Support:** Black-box machine learning models cannot explain *why* an alert was issued. AeroVital emits auditable, rule-based dominant factors and transparent confidence bounds for every observation window.

---

## System Architecture

The AeroVital end-to-end conceptual architecture spans wearable edge sensing to flight operations display:

```
Galaxy Watch / Wear OS
        ↓
Android Phone
        ↓
Django REST API
        ↓
AeroVital Core
        ↓
PostgreSQL
        ↓
React Dashboard
```

> **Implementation Phase Notice:** The **Core Engine**, **Django REST Backend**, **PostgreSQL Integration**, and **React Dashboard** are fully implemented and verified locally end-to-end. The **Galaxy Watch / Wear OS** and **Android Phone** mobile gateway layers represent the active, upcoming implementation phase. Currently, telemetry ingestion is demonstrated using controlled, deterministic flight scenarios and streaming telemetry simulators.

---

## Repository Structure

```
AeroVital/
├── backend/
│   └── core/                   # Verified AeroVital Core Intelligence Engine
│       ├── baseline/           # Pilot baseline comparison & normalization
│       ├── confidence/         # Multi-factor confidence evaluator & gating
│       ├── features/           # Time/frequency HRV & accelerometer feature extraction
│       ├── intelligence/       # Provisional rule-based state estimation & thresholds
│       ├── pipeline/           # Orchestrator connecting all pipeline stages
│       ├── preprocessing/      # Rolling temporal windowing & sample buffers
│       ├── quality/            # Multi-channel Signal Quality Assessment (SQI)
│       ├── schemas/            # Immutable Pydantic v2 domain schemas & contracts
│       ├── validation/         # Input bounds & chronological monotonicity validation
│       └── tests/              # 44 verified Core unit & integration tests
├── django-backend/             # Verified Django 6.1.1 + Django REST Framework backend
│   ├── config/                 # Settings, PostgreSQL connection, token auth, CORS
│   ├── pilots/                 # Pilot profiles, credentials, scoping permissions
│   ├── devices/                # Wearable device registration & heartbeat tracking
│   ├── missions/               # Operational sorties, flight phases, G-load tracking
│   ├── telemetry/              # Ingestion endpoints, buffering, Core integration service
│   ├── intelligence/           # State estimates, pilot baselines, model versions
│   └── alerts/                 # Real-time flight safety alerts & acknowledgment
├── web/                        # Modern React 18 / Vite 5 flight operations dashboard
│   ├── src/
│   │   ├── components/         # Modular glassmorphic UI components
│   │   ├── hooks/              # Custom hooks (useAuth, useDashboardData polling)
│   │   ├── pages/              # LoginPage, DashboardPage
│   │   ├── services/           # api.js client consuming Django REST API
│   │   ├── styles/             # Curated aviation HUD design tokens & theme
│   │   └── utils/              # Robust formatting & safety-checked conversions
│   ├── package.json            # React, Vite, Recharts, Lucide dependencies
│   └── vite.config.js          # Vite build & Vitest test runner configuration
├── android/                    # Android & Wear OS application scaffold (IN PROGRESS)
│   ├── app/                    # Wear OS Compose Kotlin project skeleton
│   └── README.md               # Detailed status of wearable sensor implementation
├── scripts/                    # Verified project execution & verification utilities
│   ├── test_engine.py          # Standalone Core engine smoke-test harness
│   └── simulator.py            # Streaming & scenario-driven Django REST telemetry client
└── intelligence/               # Formal mathematical and architectural specifications
    ├── DATA_AND_FEATURE_STRATEGY.md # Feature extraction and data tier specifications
    └── DECISION_LOGIC.md            # Structural inference and decision rules
```

---

## End-to-End Data Flow

Data flows deterministically from sensor submission to dashboard visualization:

```
Telemetry Submitted (REST / JSON)
        ↓
Core Validation (Bounds checking & chronological timestamp ordering)
        ↓
Windowing (Rolling buffer, minimum 5 samples across temporal window)
        ↓
Signal Quality (Channel usability, missing sample ratio, motion corruption)
        ↓
Feature Extraction (Mean HR, time-domain HRV [RMSSD, SDNN], accelerometer magnitude)
        ↓
Baseline Normalization (Comparison to calibrated individual pilot profile)
        ↓
State Estimation (Deterministic structural rules: Normal, Workload, Fatigue)
        ↓
Confidence Evaluation (Multi-factor scoring, quality penalty, abstention gating)
        ↓
PostgreSQL Persistence (Telemetry, FeatureWindow, SignalQuality, StateEstimate, Alert)
        ↓
Dashboard API Retrieval (Authenticated GET /current-state/, /telemetry/, /alerts/)
        ↓
Dashboard Visualization (Live HUD gauges, biometrics charts, dominant factors)
```

---

## Fatigue & Workload Intelligence

AeroVital operates under a strict, safety-critical inference contract. The engine never guesses, imputes, or defaults missing metrics.

### Verified Engine States

1. **`NORMAL`**
   - **Conditions:** Positive baseline concordance on *both* heart rate (`|ΔHR| ≤ 10 BPM`) and HRV (`RMSSD ratio ≥ 0.85`), with confirmed benign flight context (`G-load ≤ 1.2g`, phase `CRUISE`, low physical activity).
   - **Semantics:** Confirmed nominal pilot vitality.
2. **`ELEVATED_WORKLOAD`**
   - **Conditions:** Physiological activation (`ΔHR > +10 BPM` above baseline) corroborated by positive operational workload context (`G-load > 1.5g`, high-workload phase like `COMBAT_MANEUVER` or `TAKEOFF`, or high physical motion).
   - **Semantics:** Pilot is experiencing acute operational strain; physiological activation is contextually justified and distinguished from fatigue.
3. **`FATIGUE`**
   - **Conditions:** Autonomic degradation (`RMSSD ratio < 0.70` relative to calibrated baseline) paired with positively established benign context (`G-load ≤ 1.2g`, benign phase like `CRUISE`). Contradictory high-workload factors rule out this state.
   - **Semantics:** True autonomic fatigue detected under benign flight conditions, generating proactive flight advisories.
4. **`INSUFFICIENT_DATA`**
   - **Conditions:** Triggered when sensor channels are corrupted (`SQI < 0.50` or motion index `> 0.60`), required channels are missing, pilot baseline is uncalibrated, or contextual evidence is contradictory.
   - **Semantics:** The engine abstains rather than producing hazardous false positives or false negatives.

### Core Safety Principles
- **Pilot-Specific Calibrated Baselines:** Every physiological comparison is anchored to an individual pilot's resting profile (`resting_heart_rate`, `baseline_rmssd`).
- **Signal Quality & Motion Contamination:** High dynamic activity or sensor artifact triggers channel rejection before state evaluation.
- **Confidence Scoring & Abstention:** Estimates carry a continuous confidence score ($C \in [0, 1]$). Low-quality or unconfirmed estimates abstain cleanly to `INSUFFICIENT_DATA`.
- **Auditable Dominant Factors:** Every estimate outputs human-readable rationale (e.g. `Elevated heart rate (+30.0 BPM relative to baseline)`, `High G-load (3.5g)`).
- **No Data Fabrication:** Missing physiological values remain `None`; synthetic zero values or artificial smoothing are forbidden.
- **No Medical/Diagnostic Claim:** AeroVital is an engineering prototype designed for flight research and operational decision support; it does not diagnose medical conditions.

---

## Backend

The backend is built on **Django 6.1.1** and **Django REST Framework**, using **PostgreSQL** for relational persistence:

- **Authentication:** Token-based authentication (`TokenAuthentication`) with per-request pilot scoping.
- **Object-Level Security:** Test pilots and operators are strictly scoped; pilots can only inspect and ingest telemetry for their assigned identity.
- **Pipeline Orchestration:** `PipelineSessionManager` coordinates stateful `AeroVitalPipeline` instances per active mission session with chronological monotonicity validation.
- **Core Entities:**
  - `Pilot`: Flight callsign, identity, and authorization.
  - `Device`: Wearable hardware registry, connection status, and last seen timestamps.
  - `Mission`: Operational flight sortie, current phase (`CRUISE`, `COMBAT_MANEUVER`, etc.), and external G-load.
  - `Baseline`: Calibrated resting heart rate and HRV RMSSD metrics.
  - `Telemetry`: Raw and parsed physiological readings.
  - `SignalQuality`: Multi-channel SQI evaluations.
  - `FeatureWindow`: Temporal window aggregation and baseline comparison metrics.
  - `StateEstimate`: Core engine determinations, confidence, and audit evidence.
  - `Alert`: Priority safety advisories (`FATIGUE_WARNING`, `WORKLOAD_ADVISORY`, `SIGNAL_QUALITY_DEGRADED`).

---

## Dashboard

The frontend is a mission-control web application built with **React 18** and **Vite 5**:

- **Aviation Glassmorphic Design:** Curated dark HUD aesthetic with high-contrast vitality cards, telemetry trend sparklines, and state badges.
- **API-Driven Architecture:** Communicates directly with the Django REST API via [web/src/services/api.js](web/src/services/api.js).
- **Dynamic Polling:** Automatically refreshes telemetry and state estimates every 4 seconds with clean stale-data and loading indicators.
- **Defensive Rendering:** Unpopulated channels display `"N/A"` without throwing errors or calculating artificial values.
- **Zero Client-Side Calculation:** All state determinations, scores, and factors originate strictly from the backend Core Engine.

---

## Current Verification Status

| Component | Status | Verification Details |
| :--- | :--- | :--- |
| **AeroVital Core** | **VERIFIED** | 44/44 unit & integration tests passing (`pytest backend/core/tests`). |
| **Django Backend** | **VERIFIED** | 21/21 Django REST API tests passing against PostgreSQL. |
| **PostgreSQL Database** | **VERIFIED** | Relational schemas, migrations, and model persistence verified. |
| **React Dashboard** | **VERIFIED** | 8/8 comprehensive UI unit tests passing (`vitest`). Production bundle builds cleanly. |
| **Local End-to-End Flow** | **VERIFIED** | Live ingestion demonstrated across `NORMAL`, `ELEVATED_WORKLOAD`, `FATIGUE`, and `INSUFFICIENT_DATA`. |
| **Android / Wear OS** | **IN PROGRESS** | Gradle build and initial Wear Compose scaffold created; Samsung Health SDK sensor streaming in progress. |
| **Production Cloud Hosting**| **PLANNED** | Containerized deployment (Docker, Kubernetes) and cloud database provisioning. |

---

## Local Development & Startup

### Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- PostgreSQL 14+ running locally (database: `aerovital`)

### 1. Database Setup
Ensure PostgreSQL is active and initialize the database:
```bash
# Create database and user (if not already existing)
psql -U postgres -c "CREATE USER aerovital_user WITH PASSWORD 'aerovital_password';"
psql -U postgres -c "CREATE DATABASE aerovital OWNER aerovital_user;"
```

### 2. Backend Setup
```bash
# Navigate to backend directory
cd django-backend

# Set up virtual environment and install dependencies
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the Django development server
python manage.py runserver 127.0.0.1:8000
```

### 3. Frontend Setup
```bash
# Navigate to web dashboard directory
cd web

# Install dependencies
npm install

# Start Vite development server
npm run dev -- --port 3000
```
Open **`http://localhost:3000`** in your browser.

### 4. Telemetry Streaming & Scenario Testing
To stream verified flight telemetry into the live system:
```bash
# From repository root (with virtual environment active)
python scripts/simulator.py --scenario normal
python scripts/simulator.py --scenario workload
python scripts/simulator.py --scenario fatigue
python scripts/simulator.py --scenario insufficient
```

---

## Testing

Run the test suites across all project layers:

```bash
# 1. AeroVital Core Tests (Unit, Schema, Rules, Confidence, Pipeline)
pytest backend/core/tests/

# 2. Django Backend & PostgreSQL API Tests
cd django-backend
python manage.py test

# 3. React Dashboard Tests (Vitest + React Testing Library)
cd web
npm test

# 4. React Production Bundle Validation
npm run build
```

---

## Security Guidelines

- **Environment Variables:** All secrets (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`) must be supplied via local environment variables or untracked `.env` files.
- **No Committed Secrets:** Never commit `.env` files, API keys, private certificates, or PostgreSQL data directories.
- **Frontend Hygiene:** The React client contains zero hardcoded API secrets or private keys; all communication is authenticated via transient session tokens stored in secure local storage.
- **Database Segregation:** PostgreSQL data directories (`postgres_data/`) and SQLite scratch files are strictly excluded from version control.

---

## Limitations

- **Wear OS Implementation:** Hardware sensor streaming from Samsung Galaxy Watch devices is actively in progress; current end-to-end demonstrations use verified synthetic telemetry streams.
- **Polling Architecture:** The dashboard currently synchronizes telemetry via REST polling (4-second interval). High-frequency real-time flight telemetry will transition to WebSockets in a future milestone.
- **Research Prototype:** AeroVital algorithms represent engineering research prototypes and are not clinically validated or certified by the FAA, EASA, or FDA for medical diagnosis or operational flight clearance.

---

## Future Roadmap

1. **Wear OS Sensor Integration:** Implement the Samsung Privileged Health SDK adapter on Galaxy Watch 4/5/6 for real-time PPG and ECG capture.
2. **Mobile Gateway Application:** Finalize the companion Android phone application with local Room DB store-and-forward caching for communication loss during flight.
3. **Real-Time WebSockets:** Replace REST polling with Django Channels / WebSockets for low-latency (<100ms) telemetry streaming.
4. **Physiological Baseline Calibration Engine:** Automated in-flight baseline recalibration during stable, unaccelerated cruise phases.
5. **Multi-Crew Cockpit Monitoring:** Support multi-pilot cockpit situational displays and flight surgeon ground stations.
