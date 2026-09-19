# AeroVital

AeroVital is a research-oriented aviation physiological monitoring and fatigue assessment system.

## Architecture
The system supports two parallel paths for physiological telemetry:
1. **Real Sensor Path**: Wear OS → physiological acquisition → preprocessing → feature extraction → fatigue engine → backend/API → web dashboard
2. **Synthetic Telemetry Path**: Synthetic telemetry → same preprocessing/features → same fatigue engine → backend/API → web dashboard

## Modules
- `android/`: Wear OS data acquisition application.
- `backend/`: FastAPI Python application with a deterministic fatigue engine.
- `web/`: React/Vite dashboard to view telemetry and fatigue states.
- `scripts/`: Synthetic data simulators.

## Getting Started

### 1. Run the Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

### 2. Run the Synthetic Telemetry Simulator
```bash
source .venv/bin/activate
python scripts/simulator.py --duration 10 --interval 1.0
```

### 3. Run the Web Dashboard
```bash
cd web
npm install
npm run dev
```

## Running Tests
```bash
pytest backend/tests/
```
