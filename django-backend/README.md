# AeroVital Backend

## Requirements
- Python 3.13+
- PostgreSQL
- Django
- Django REST Framework

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

3. Copy .env.example to .env:

   Copy-Item .env.example .env

4. Update .env with the local PostgreSQL credentials.

## Database

Create a PostgreSQL database named erovital.

Run migrations:

   python manage.py migrate

Check migration status:

   python manage.py showmigrations

## Run the Backend

   python manage.py runserver

The API is available at:

   http://127.0.0.1:8000/

## Verification

Run:

   python manage.py check

   python manage.py makemigrations --check --dry-run

   python manage.py test

## Main API Endpoints

- /api/ — Telemetry list/create
- /api/alerts/ — Alerts list/create
- /api/mission-events/ — Mission events list/create
- /api/state-estimates/ — State estimates

## Database

The backend uses PostgreSQL through Django's database configuration.

## Core Integration

The backend is intended to integrate with the AeroVital Core Engine through the defined Core input and result contracts. The backend must not duplicate the Core fatigue algorithm.

## Scope

This verification covers backend software, data flow, persistence, API behavior, and integration readiness. It is not medical, clinical, aviation, or certification validation.
