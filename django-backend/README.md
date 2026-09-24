# AeroVital Backend

## Requirements
- Python 3.12+
- PostgreSQL
- Django
- Django REST Framework

## Setup

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   ```

4. Update `.env` with your PostgreSQL credentials.

## Database

Create a PostgreSQL database named `aerovital`:
```bash
createdb aerovital
```

Run migrations:
```bash
python manage.py migrate
```

Check migration status:
```bash
python manage.py showmigrations
```

## Run the Backend

```bash
python manage.py runserver
```

The API is available at:
`http://127.0.0.1:8000/`

## Verification

Run:
```bash
python manage.py check
python manage.py test
```

## Main API Endpoints (v1)

- `/api/v1/auth/` - Token authentication
- `/api/v1/pilots/` - Pilot profiles
- `/api/v1/devices/` - Device registry
- `/api/v1/missions/` - Missions & operational context
- `/api/v1/telemetry/` - Telemetry ingestion & query
- `/api/v1/telemetry/signal-quality/` - Signal quality assessments
- `/api/v1/telemetry/features/` - Feature windows
- `/api/v1/intelligence/baselines/` - Pilot calibrated baselines
- `/api/v1/intelligence/state-estimates/` - Fatigue state estimates
- `/api/v1/intelligence/current-state/` - Current state summary
- `/api/v1/alerts/` - Real-time alerts
- `/api/v1/alerts/mission-events/` - Mission operational events

## Core Integration

The backend integrates with the AeroVital Core Engine (`backend/core/`) through standardized input and result contracts. The backend orchestrates Core validation, windowing, signal quality, baseline normalization, and fatigue estimation without duplicating intelligence algorithms.
