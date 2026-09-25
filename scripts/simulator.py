#!/usr/bin/env python3
"""AeroVital Synthetic Flight Telemetry Stream Simulator.

Sends realistic continuous or scenario-driven flight telemetry to the verified
AeroVital Django REST Backend (`/api/v1/telemetry/`).

Demonstrates streaming biometric and flight context into the live pipeline:
- Heart Rate (BPM)
- Beat-to-Beat RR Intervals (ms)
- Blood Oxygen Saturation (SpO2 %)
- Skin Temperature (°C)
- 3-Axis Accelerometer (G)
- Mission Phase and External G-load

Usage:
    python scripts/simulator.py --scenario normal
    python scripts/simulator.py --scenario workload
    python scripts/simulator.py --scenario fatigue
    python scripts/simulator.py --scenario insufficient
    python scripts/simulator.py --stream --duration 5 --interval 2.0
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
import sys
import time
import urllib.request
import urllib.error

DEFAULT_API_BASE = "http://127.0.0.1:8000/api/v1"
DEFAULT_TOKEN = "25d1f9a110a39b51eb81bed93c8b3d1199c03dec"
DEFAULT_PILOT_ID = "fdce995a-7dcd-4ebc-a588-5a002c8c84f6"  # Capt. John Miller (pilot_alpha)
DEFAULT_DEVICE_ID = "aa12ad2a-aa6a-493e-b91f-e8d98290eeb2" # WATCH-PG-001
CRUISE_MISSION_ID = "f3b9dace-3b5a-456c-ba0c-88023197faa5" # SORTIE-PG-01 (CRUISE, 1.0g)
WORKLOAD_MISSION_ID = "29d71df1-c71c-4605-9747-b69e5ab747ac" # SORTIE-PG-WORKLOAD (COMBAT, 3.5g)


def post_sample(api_base: str, token: str, sample_payload: dict) -> dict:
    url = f"{api_base.rstrip('/')}/telemetry/"
    data = json.dumps(sample_payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Token {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_scenario(scenario: str, api_base: str, token: str):
    print(f"\n[AeroVital Simulator] Executing Scenario: {scenario.upper()}")
    now = datetime.now(timezone.utc)

    scenarios = {
        "normal": {
            "mission": CRUISE_MISSION_ID,
            "hr": 67.0,
            "rr": [900.0, 950.0, 900.0, 950.0, 900.0],
            "g": 1.0,
            "accel": (0.0, 0.0, 1.0),
            "expected": "NORMAL",
        },
        "workload": {
            "mission": WORKLOAD_MISSION_ID,
            "hr": 95.0,
            "rr": [630.0, 635.0, 630.0, 635.0, 630.0],
            "g": 3.5,
            "accel": (0.2, 0.3, 3.5),
            "expected": "ELEVATED_WORKLOAD",
        },
        "fatigue": {
            "mission": CRUISE_MISSION_ID,
            "hr": 67.0,
            "rr": [850.0, 860.0, 850.0, 860.0, 850.0],
            "g": 1.0,
            "accel": (0.0, 0.0, 1.0),
            "expected": "FATIGUE",
        },
        "insufficient": {
            "mission": CRUISE_MISSION_ID,
            "hr": 66.0,
            "rr": None,
            "g": 1.0,
            "accel": (0.0, 0.0, 1.0),
            "expected": "INSUFFICIENT_DATA",
        },
    }

    cfg = scenarios[scenario]
    for i in range(6):
        ts = now + timedelta(seconds=i * 2)
        payload = {
            "pilot": DEFAULT_PILOT_ID,
            "device": DEFAULT_DEVICE_ID,
            "mission": cfg["mission"],
            "timestamp": ts.isoformat(),
            "heart_rate": cfg["hr"],
            "rr_interval": cfg["rr"],
            "spo2": 98.0,
            "skin_temperature": 36.5,
            "accel_x": cfg["accel"][0],
            "accel_y": cfg["accel"][1],
            "accel_z": cfg["accel"][2],
            "battery_level": 95.0,
        }
        res = post_sample(api_base, token, payload)
        print(f"  Sample {i+1}/6 (ts: {ts.strftime('%H:%M:%S')}) -> Status: {res.get('status')}")
        if res.get("estimate"):
            est = res["estimate"]
            print(f"  >>> Core State: {est.get('fatigue_state')} | Conf: {est.get('confidence')} | SQI: {est.get('overall_sqi')}")
            print(f"  >>> Factors: {est.get('dominant_factors')}")
            if res.get("alert"):
                print(f"  >>> Alert Dispatched: {res['alert']['alert_type']} ({res['alert']['severity']})")


def run_stream(duration_min: int, interval_sec: float, api_base: str, token: str):
    print(f"\n[AeroVital Simulator] Streaming continuous telemetry for {duration_min} min every {interval_sec}s...")
    start = time.time()
    end = start + (duration_min * 60)
    step = 0

    while time.time() < end:
        ts = datetime.now(timezone.utc)
        payload = {
            "pilot": DEFAULT_PILOT_ID,
            "device": DEFAULT_DEVICE_ID,
            "mission": CRUISE_MISSION_ID,
            "timestamp": ts.isoformat(),
            "heart_rate": 68.0 + (step % 5),
            "rr_interval": [880.0, 910.0, 890.0, 920.0, 900.0],
            "spo2": 98.0,
            "skin_temperature": 36.5,
            "accel_x": 0.0,
            "accel_y": 0.0,
            "accel_z": 1.0,
            "battery_level": 94.0,
        }
        try:
            res = post_sample(api_base, token, payload)
            step += 1
            print(f"[{ts.strftime('%H:%M:%S')}] Sample #{step} ingested -> pipeline status: {res.get('status')}")
        except Exception as err:
            print(f"[{ts.strftime('%H:%M:%S')}] Ingestion error: {err}")
        time.sleep(interval_sec)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AeroVital Verified Telemetry Simulator")
    parser.add_argument("--scenario", choices=["normal", "workload", "fatigue", "insufficient"], help="Run discrete verified scenario")
    parser.add_argument("--stream", action="store_true", help="Stream continuous telemetry")
    parser.add_argument("--duration", type=int, default=5, help="Stream duration in minutes")
    parser.add_argument("--interval", type=float, default=2.0, help="Stream interval in seconds")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="Django API base URL")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Auth token")

    args = parser.parse_args()

    if args.scenario:
        run_scenario(args.scenario, args.api_base, args.token)
    elif args.stream:
        run_stream(args.duration, args.interval, args.api_base, args.token)
    else:
        # Default behavior: run normal scenario
        run_scenario("normal", args.api_base, args.token)
