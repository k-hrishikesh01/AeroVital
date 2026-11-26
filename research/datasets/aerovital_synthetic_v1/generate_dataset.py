#!/usr/bin/env python3
"""AeroVital Synthetic Physiological Dataset Generator.

Generates a reproducible, high-fidelity research dataset consisting of:
- 30 synthetic participant profiles with individualized resting baselines.
- 60 flight sessions across 5 distinct human-factors and operational scenarios:
    1. NORMAL_BASELINE
    2. ELEVATED_COGNITIVE_WORKLOAD
    3. FATIGUE_PHYSIOLOGICAL
    4. DEGRADED_SIGNAL_QUALITY
    5. MIXED_OPERATIONAL_CONDITIONS
- 216,000 timestamped 1 Hz telemetry observations (60 sessions x 3,600 observations).
- Mathematically consistent heart rate and beat-to-beat intervals (RR intervals).
- Strict non-fabrication: channels not provided by the Wear OS hardware (ECG, SpO2, skin temp)
  are represented as null (None), never zero.

Operational Isolation:
- Tagged with data_source="SYNTHETIC", is_synthetic=True, dataset_id="aerovital-synthetic-v1".
- Fixed random seed (42) for deterministic reproducibility.
"""

import csv
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Configuration constants
RANDOM_SEED = 42
DATASET_ID = "aerovital-synthetic-v1"
GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
NOMINAL_SAMPLING_HZ = 1.0
SESSION_DURATION_SEC = 3600  # 1 hour per session
NUM_PARTICIPANTS = 30
SESSIONS_PER_PARTICIPANT = 2
TOTAL_SESSIONS = NUM_PARTICIPANTS * SESSIONS_PER_PARTICIPANT  # 60 sessions
TOTAL_OBSERVATIONS = TOTAL_SESSIONS * SESSION_DURATION_SEC   # 216,000 observations

OUTPUT_DIR = Path(__file__).resolve().parent

SCENARIO_NAMES = [
    "NORMAL_BASELINE",
    "ELEVATED_COGNITIVE_WORKLOAD",
    "FATIGUE_PHYSIOLOGICAL",
    "DEGRADED_SIGNAL_QUALITY",
    "MIXED_OPERATIONAL_CONDITIONS",
]


def generate_participant_profiles(seed: int) -> List[Dict[str, Any]]:
    """Generate 30 synthetic participant profiles with individualized physiological baselines."""
    rng = np.random.default_rng(seed)
    profiles = []

    for i in range(1, NUM_PARTICIPANTS + 1):
        pilot_id = f"SYN-P{i:03d}"
        
        # Resting HR: mean ~65 bpm, std ~5.5 bpm, bounds [54, 78]
        resting_hr = round(float(np.clip(rng.normal(65.0, 5.5), 54.0, 78.0)), 1)
        
        # Baseline RMSSD: log-normal distribution, median ~45 ms, bounds [30, 72]
        baseline_rmssd = round(float(np.clip(rng.lognormal(mean=3.78, sigma=0.22), 30.0, 72.0)), 1)
        
        # Baseline SDNN: correlated with RMSSD (~1.3x RMSSD with noise)
        baseline_sdnn = round(float(np.clip(baseline_rmssd * rng.uniform(1.2, 1.45), baseline_rmssd + 5.0, 95.0)), 1)
        
        # Mean RR in milliseconds: 60000 / resting_hr
        baseline_mean_rr = round(60000.0 / resting_hr, 1)

        # Baseline calibration date
        cal_date = datetime(2026, 10, 15, 8, 30, 0, tzinfo=timezone.utc) + timedelta(days=i)

        profiles.append({
            "pilot_id": pilot_id,
            "callsign": f"VITAL-{i:02d}",
            "age": int(rng.integers(26, 48)),
            "baseline_version": f"CAL-2026-{i:03d}",
            "calibration_timestamp": cal_date.isoformat(),
            "resting_heart_rate": resting_hr,
            "baseline_rmssd": baseline_rmssd,
            "baseline_sdnn": baseline_sdnn,
            "baseline_mean_rr": baseline_mean_rr,
            "calibration_duration_sec": 600,
            "is_calibrated": True,
            "assigned_scenario_group": SCENARIO_NAMES[(i - 1) // 6],  # 6 participants per scenario
        })

    return profiles


def simulate_session_timeseries(
    participant: Dict[str, Any],
    session_index: int,
    scenario: str,
    start_time: datetime,
    session_seed: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Simulate a single 3,600-second session at 1 Hz for a participant under a given scenario."""
    rng = np.random.default_rng(session_seed)
    
    session_id = f"SYN-S{(session_index):03d}"
    pilot_id = participant["pilot_id"]
    base_hr = participant["resting_heart_rate"]
    base_rmssd = participant["baseline_rmssd"]

    records: List[Dict[str, Any]] = []

    # Time array: 0 to 3599 seconds
    t = np.arange(SESSION_DURATION_SEC)

    # Initialize physiological state vectors
    target_hr = np.zeros(SESSION_DURATION_SEC)
    target_rmssd = np.zeros(SESSION_DURATION_SEC)
    g_load = np.ones(SESSION_DURATION_SEC)
    flight_phases = ["CRUISE"] * SESSION_DURATION_SEC
    motion_intensity = np.zeros(SESSION_DURATION_SEC)
    accel_noise_scale = np.zeros(SESSION_DURATION_SEC)
    dropout_mask = np.zeros(SESSION_DURATION_SEC, dtype=bool)

    # Common background rhythms:
    # Respiratory Sinus Arrhythmia (RSA, HF: ~0.25 Hz)
    # Mayer waves / Baroreflex (LF: ~0.10 Hz)
    # Slow drift (VLF: ~0.01 Hz)
    rsa_phase = rng.uniform(0, 2 * np.pi)
    mayer_phase = rng.uniform(0, 2 * np.pi)
    drift_phase = rng.uniform(0, 2 * np.pi)

    rsa = 2.5 * np.sin(2 * np.pi * 0.25 * t + rsa_phase)
    mayer = 3.5 * np.sin(2 * np.pi * 0.09 * t + mayer_phase)
    drift = 1.5 * np.sin(2 * np.pi * 0.005 * t + drift_phase)

    if scenario == "NORMAL_BASELINE":
        # Stable benign cruise, HR near baseline, RMSSD near baseline, high SQI
        target_hr = base_hr + rsa * 0.6 + mayer * 0.5 + drift * 0.5 + rng.normal(0, 0.4, SESSION_DURATION_SEC)
        target_rmssd = base_rmssd * np.clip(1.0 + 0.08 * np.sin(2 * np.pi * 0.003 * t) + rng.normal(0, 0.04, SESSION_DURATION_SEC), 0.85, 1.20)
        g_load = 1.0 + rng.normal(0, 0.02, SESSION_DURATION_SEC)
        flight_phases = ["CRUISE"] * SESSION_DURATION_SEC
        motion_intensity = np.clip(0.04 + rng.normal(0, 0.01, SESSION_DURATION_SEC), 0.01, 0.08)
        accel_noise_scale = 0.02

        # < 0.5% isolated single packet drops
        dropout_indices = rng.choice(SESSION_DURATION_SEC, size=int(0.003 * SESSION_DURATION_SEC), replace=False)
        dropout_mask[dropout_indices] = True

    elif scenario == "ELEVATED_COGNITIVE_WORKLOAD":
        # Elevated HR (+22 to +42 bpm), suppressed RMSSD (sympathetic activation), high G-load, high-workload phases
        # Dynamic workload profile across the hour:
        # Phase 1: 0-600s: TAKEOFF & CLIMB (HR +18, G 1.4)
        # Phase 2: 600-1800s: CRUISE & COMBAT PREP (HR +12, G 1.1)
        # Phase 3: 1800-2700s: COMBAT_MANEUVER / HIGH_G (HR +35, G 3.2-4.5)
        # Phase 4: 2700-3600s: HIGH-SPEED DESCENT & COMBAT (HR +28, G 2.2-3.0)
        elevation = np.zeros(SESSION_DURATION_SEC)
        for s in range(SESSION_DURATION_SEC):
            if s < 600:
                flight_phases[s] = "CLIMB"
                elevation[s] = 18.0 + 4.0 * np.sin(s / 60.0)
                g_load[s] = 1.4 + 0.1 * np.sin(s / 20.0)
                motion_intensity[s] = 0.35
            elif s < 1800:
                flight_phases[s] = "CRUISE"
                elevation[s] = 12.0 + 3.0 * np.sin(s / 80.0)
                g_load[s] = 1.1 + 0.05 * np.sin(s / 30.0)
                motion_intensity[s] = 0.20
            elif s < 2700:
                flight_phases[s] = "COMBAT_MANEUVER"
                elevation[s] = 34.0 + 6.0 * np.sin(s / 40.0)
                g_load[s] = 3.2 + 0.9 * np.sin(s / 15.0)
                motion_intensity[s] = 0.65
            else:
                flight_phases[s] = "COMBAT_MANEUVER"
                elevation[s] = 26.0 + 5.0 * np.sin(s / 50.0)
                g_load[s] = 2.4 + 0.6 * np.sin(s / 25.0)
                motion_intensity[s] = 0.50

        target_hr = base_hr + elevation + rsa * 0.3 + mayer * 0.8 + rng.normal(0, 0.8, SESSION_DURATION_SEC)
        # RMSSD significantly suppressed under sympathetic stimulation (~16-24 ms)
        target_rmssd = np.clip(base_rmssd * 0.42 * (1.0 - elevation / 65.0) + rng.normal(0, 1.2, SESSION_DURATION_SEC), 14.0, 26.0)
        accel_noise_scale = 0.12

        # ~1% drops due to heavy physical G-buffeting
        dropout_indices = rng.choice(SESSION_DURATION_SEC, size=int(0.01 * SESSION_DURATION_SEC), replace=False)
        dropout_mask[dropout_indices] = True

    elif scenario == "FATIGUE_PHYSIOLOGICAL":
        # Extended benign cruise: HR near or below baseline, severe autonomic degradation (RMSSD < 50% baseline), low motion
        # Pilot enters with mild fatigue and progresses into deep autonomic exhaustion
        fatigue_drift = np.linspace(0.0, -4.0, SESSION_DURATION_SEC)  # slight bradycardic drift
        
        # Occasional micro-arousal spikes every 600-800 seconds (sudden transient HR kick then collapse)
        micro_arousals = np.zeros(SESSION_DURATION_SEC)
        for spike_t in [720, 1540, 2380, 3150]:
            if spike_t < SESSION_DURATION_SEC - 40:
                window = np.exp(-np.linspace(0, 4, 30)) * 7.5
                micro_arousals[spike_t:spike_t + 30] += window

        target_hr = base_hr + fatigue_drift + micro_arousals + rsa * 0.4 + mayer * 0.3 + rng.normal(0, 0.4, SESSION_DURATION_SEC)
        
        # RMSSD progressively decreases from 55% down to 35% of baseline (vagal exhaustion)
        rmssd_decay = np.linspace(0.52, 0.36, SESSION_DURATION_SEC)
        target_rmssd = np.clip(base_rmssd * rmssd_decay + rng.normal(0, 0.8, SESSION_DURATION_SEC), 12.0, 24.0)

        g_load = 1.0 + rng.normal(0, 0.015, SESSION_DURATION_SEC)
        flight_phases = ["CRUISE"] * SESSION_DURATION_SEC
        motion_intensity = np.clip(0.02 + rng.normal(0, 0.005, SESSION_DURATION_SEC), 0.005, 0.04)
        accel_noise_scale = 0.015

        # ~0.5% drops
        dropout_indices = rng.choice(SESSION_DURATION_SEC, size=int(0.005 * SESSION_DURATION_SEC), replace=False)
        dropout_mask[dropout_indices] = True

    elif scenario == "DEGRADED_SIGNAL_QUALITY":
        # Poor sensor contact, loose strap, high motion corruption, large missingness (30-40%)
        target_hr = base_hr + rsa * 0.5 + mayer * 0.5 + rng.normal(0, 1.5, SESSION_DURATION_SEC)
        target_rmssd = np.clip(base_rmssd * rng.uniform(0.7, 1.1, SESSION_DURATION_SEC), 25.0, 60.0)
        g_load = 1.0 + rng.normal(0, 0.08, SESSION_DURATION_SEC)
        flight_phases = ["CRUISE"] * SESSION_DURATION_SEC
        motion_intensity = np.clip(0.70 + rng.normal(0, 0.15, SESSION_DURATION_SEC), 0.3, 1.2)
        accel_noise_scale = 0.45

        # Create bursty dropout periods (loose sensor slipping)
        # Block dropouts of 10-60 seconds each
        num_blocks = rng.integers(15, 25)
        for _ in range(num_blocks):
            block_start = rng.integers(0, SESSION_DURATION_SEC - 60)
            block_len = rng.integers(15, 65)
            dropout_mask[block_start:block_start + block_len] = True

        # Plus random single drops
        random_drops = rng.choice(SESSION_DURATION_SEC, size=int(0.10 * SESSION_DURATION_SEC), replace=False)
        dropout_mask[random_drops] = True

    elif scenario == "MIXED_OPERATIONAL_CONDITIONS":
        # Multi-phase operational sortie:
        # 0 - 300s:    PRE_FLIGHT & TAXI (nominal, mild anticipation)
        # 300 - 750s:  TAKEOFF & CLIMB (elevated HR +15 bpm, G 1.4-1.8)
        # 750 - 1500s: STABILIZED CRUISE (benign context, nominal recovery)
        # 1500 - 2200s: COMBAT_MANEUVER / HIGH_G (tactical engagement, HR +36 bpm, G 3.2-4.2g)
        # 2200 - 2500s: RECOVERY (deceleration back towards baseline)
        # 2500 - 3150s: EXTENDED CRUISE with progressive fatigue onset (RMSSD decline)
        # 3150 - 3450s: APPROACH (cockpit activation, HR +10 bpm)
        # 3450 - 3600s: LANDING & POST_FLIGHT
        for s in range(SESSION_DURATION_SEC):
            if s < 300:
                flight_phases[s] = "PRE_FLIGHT"
                target_hr[s] = base_hr + 4.0 + rng.normal(0, 0.5)
                target_rmssd[s] = base_rmssd * 0.95
                g_load[s] = 1.0 + rng.normal(0, 0.01)
                motion_intensity[s] = 0.15
            elif s < 750:
                flight_phases[s] = "CLIMB"
                progress = (s - 300) / 450.0
                target_hr[s] = base_hr + 15.0 * progress + rng.normal(0, 0.8)
                target_rmssd[s] = base_rmssd * (1.0 - 0.35 * progress)
                g_load[s] = 1.4 + 0.2 * np.sin(s / 20.0)
                motion_intensity[s] = 0.35
            elif s < 1500:
                flight_phases[s] = "CRUISE"
                target_hr[s] = base_hr + 2.0 + rsa[s] * 0.5 + mayer[s] * 0.4
                target_rmssd[s] = base_rmssd * 1.02
                g_load[s] = 1.0 + rng.normal(0, 0.02)
                motion_intensity[s] = 0.05
            elif s < 2200:
                flight_phases[s] = "COMBAT_MANEUVER"
                target_hr[s] = base_hr + 35.0 + 5.0 * np.sin(s / 30.0) + rng.normal(0, 1.2)
                target_rmssd[s] = np.clip(base_rmssd * 0.38 + rng.normal(0, 1.0), 15.0, 24.0)
                g_load[s] = 3.4 + 0.8 * np.sin(s / 12.0)
                motion_intensity[s] = 0.65
            elif s < 2500:
                # Recovery kinetics: exponential decay of heart rate back towards baseline
                recovery_p = (s - 2200) / 300.0
                decay = np.exp(-3.0 * recovery_p)
                target_hr[s] = base_hr + 35.0 * decay + 2.0 + rng.normal(0, 0.7)
                target_rmssd[s] = base_rmssd * (0.40 + 0.45 * (1.0 - decay))
                flight_phases[s] = "CRUISE"
                g_load[s] = 1.05 + 0.05 * decay
                motion_intensity[s] = 0.10 + 0.25 * decay
            elif s < 3150:
                # Extended cruise with progressive fatigue onset
                fatigue_prog = (s - 2500) / 650.0
                target_hr[s] = base_hr - 1.5 * fatigue_prog + rng.normal(0, 0.4)
                target_rmssd[s] = np.clip(base_rmssd * (0.85 - 0.48 * fatigue_prog) + rng.normal(0, 0.8), 14.0, 45.0)
                flight_phases[s] = "CRUISE"
                g_load[s] = 1.0 + rng.normal(0, 0.015)
                motion_intensity[s] = 0.03
            elif s < 3450:
                flight_phases[s] = "APPROACH"
                target_hr[s] = base_hr + 12.0 + rng.normal(0, 0.6)
                target_rmssd[s] = base_rmssd * 0.65
                g_load[s] = 1.15 + 0.08 * np.sin(s / 25.0)
                motion_intensity[s] = 0.25
            else:
                flight_phases[s] = "LANDING"
                target_hr[s] = base_hr + 8.0 + rng.normal(0, 0.5)
                target_rmssd[s] = base_rmssd * 0.75
                g_load[s] = 1.25 + 0.2 * np.exp(-((s - 3470) ** 2) / 100.0)  # touchdown bump
                motion_intensity[s] = 0.30

        accel_noise_scale = 0.08
        # ~1.5% intermittent drops during high-maneuver phases
        maneuver_mask = (g_load > 2.5)
        maneuver_indices = np.where(maneuver_mask)[0]
        if len(maneuver_indices) > 0:
            drops = rng.choice(maneuver_indices, size=min(len(maneuver_indices), 25), replace=False)
            dropout_mask[drops] = True

    # Clip target HR and target RMSSD to strict physiological bounds
    target_hr = np.clip(target_hr, 42.0, 185.0)
    target_rmssd = np.clip(target_rmssd, 10.0, 110.0)

    # Generate sequential observations
    session_start_iso = start_time.isoformat()
    last_valid_rr = 60000.0 / target_hr[0]

    for sec in range(SESSION_DURATION_SEC):
        current_ts = start_time + timedelta(seconds=sec)
        ts_iso = current_ts.isoformat()

        if dropout_mask[sec]:
            # Sensor dropout: physiological channels are strictly None (null)
            records.append({
                "timestamp": ts_iso,
                "participant_id": pilot_id,
                "session_id": session_id,
                "scenario": scenario,
                "heart_rate": None,
                "rr_interval": None,
                "spo2": None,
                "skin_temperature": None,
                "activity_level": "UNKNOWN" if scenario == "DEGRADED_SIGNAL_QUALITY" else "STATIONARY",
                "steps": None,
                "accel_x": round(float(rng.normal(0.0, 0.5 if scenario == "DEGRADED_SIGNAL_QUALITY" else 0.03)), 3),
                "accel_y": round(float(rng.normal(0.0, 0.5 if scenario == "DEGRADED_SIGNAL_QUALITY" else 0.03)), 3),
                "accel_z": round(float(rng.normal(1.0, 0.5 if scenario == "DEGRADED_SIGNAL_QUALITY" else 0.03)), 3),
                "battery_level": round(max(5.0, 98.0 - (sec / 3600.0) * 8.5), 1),
                "mission_phase": flight_phases[sec],
                "external_g_load": round(float(g_load[sec]), 2),
                "flight_duration_sec": sec,
                "data_source": "SYNTHETIC",
                "dataset_id": DATASET_ID,
                "is_synthetic": True,
            })
            continue

        # Valid observation:
        curr_hr = target_hr[sec]
        curr_rmssd = target_rmssd[sec]

        # Determine beat count in this 1-second interval
        # E.g. at 60 bpm -> 1 beat/sec; at 120 bpm -> 2 beats/sec
        num_beats = max(1, int(round(curr_hr / 60.0)))
        
        # Calculate target mean RR interval
        target_mean_rr = 60000.0 / curr_hr

        # Generate realistic successive beat intervals
        # Autoregressive generation ensuring successive difference variance ~ curr_rmssd^2
        rr_list: List[float] = []
        for b in range(num_beats):
            # Successive difference delta ~ N(0, curr_rmssd)
            delta = rng.normal(0, curr_rmssd * 0.95)
            # Pull towards target mean to prevent random walk drift
            pull = 0.25 * (target_mean_rr - last_valid_rr)
            rr_val = np.clip(last_valid_rr + delta + pull, 325.0, 1420.0)
            rr_list.append(round(float(rr_val), 1))
            last_valid_rr = rr_val

        # Mathematically concordant instantaneous HR: 60000 / mean(rr_list)
        packet_hr = round(float(60000.0 / np.mean(rr_list)), 1)

        # Accelerometer simulation
        # At 1.0g resting, z ~ 1.0, x ~ 0.0, y ~ 0.0
        # Under external G-load, z-axis reflects aircraft G + micro body vibration
        curr_g = g_load[sec]
        noise_sd = accel_noise_scale if scenario != "DEGRADED_SIGNAL_QUALITY" else 0.35
        ax = round(float(rng.normal(0.0, noise_sd)), 3)
        ay = round(float(rng.normal(0.0, noise_sd)), 3)
        az = round(float(curr_g + rng.normal(0.0, noise_sd)), 3)

        # Activity level string
        act_intensity = motion_intensity[sec]
        if act_intensity > 0.55:
            act_str = "HIGH_MANEUVER"
        elif act_intensity > 0.25:
            act_str = "MODERATE"
        else:
            act_str = "REST"

        records.append({
            "timestamp": ts_iso,
            "participant_id": pilot_id,
            "session_id": session_id,
            "scenario": scenario,
            "heart_rate": packet_hr,
            "rr_interval": rr_list if len(rr_list) > 1 else rr_list[0],
            "spo2": None,  # Hardware non-fabrication
            "skin_temperature": None,  # Hardware non-fabrication
            "activity_level": act_str,
            "steps": None,
            "accel_x": ax,
            "accel_y": ay,
            "accel_z": az,
            "battery_level": round(max(5.0, 98.0 - (sec / 3600.0) * 8.5), 1),
            "mission_phase": flight_phases[sec],
            "external_g_load": round(float(curr_g), 2),
            "flight_duration_sec": sec,
            "data_source": "SYNTHETIC",
            "dataset_id": DATASET_ID,
            "is_synthetic": True,
        })

    # Compute session-level summary metrics
    valid_hrs = [r["heart_rate"] for r in records if r["heart_rate"] is not None]
    valid_rrs: List[float] = []
    for r in records:
        if r["rr_interval"] is not None:
            if isinstance(r["rr_interval"], list):
                valid_rrs.extend(r["rr_interval"])
            else:
                valid_rrs.append(r["rr_interval"])

    # Calculate actual empirical HRV metrics for the session
    if len(valid_rrs) > 2:
        diffs = np.diff(valid_rrs)
        actual_rmssd = round(float(np.sqrt(np.mean(diffs ** 2))), 1)
        actual_sdnn = round(float(np.std(valid_rrs)), 1)
        actual_pnn50 = round(float(100.0 * np.sum(np.abs(diffs) > 50.0) / len(diffs)), 1)
    else:
        actual_rmssd = None
        actual_sdnn = None
        actual_pnn50 = None

    session_summary = {
        "session_id": session_id,
        "participant_id": pilot_id,
        "scenario": scenario,
        "start_time": session_start_iso,
        "end_time": (start_time + timedelta(seconds=SESSION_DURATION_SEC)).isoformat(),
        "duration_sec": SESSION_DURATION_SEC,
        "total_observations": SESSION_DURATION_SEC,
        "valid_observations": len(valid_hrs),
        "missing_observations": SESSION_DURATION_SEC - len(valid_hrs),
        "missing_rate_pct": round(100.0 * (SESSION_DURATION_SEC - len(valid_hrs)) / SESSION_DURATION_SEC, 2),
        "hr_mean": round(float(np.mean(valid_hrs)), 1) if valid_hrs else None,
        "hr_min": round(float(np.min(valid_hrs)), 1) if valid_hrs else None,
        "hr_max": round(float(np.max(valid_hrs)), 1) if valid_hrs else None,
        "rr_interval_count": len(valid_rrs),
        "empirical_rmssd_ms": actual_rmssd,
        "empirical_sdnn_ms": actual_sdnn,
        "empirical_pnn50_pct": actual_pnn50,
        "baseline_resting_hr": base_hr,
        "baseline_rmssd": base_rmssd,
    }

    return session_summary, records


def main():
    print(f"===============================================================")
    print(f" AeroVital Synthetic Dataset Generator v{GENERATOR_VERSION}")
    print(f" Target: {NUM_PARTICIPANTS} Participants | {TOTAL_SESSIONS} Sessions | {TOTAL_OBSERVATIONS} Records")
    print(f" Fixed Random Seed: {RANDOM_SEED}")
    print(f" Output Directory: {OUTPUT_DIR}")
    print(f"===============================================================\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Generate participants
    print("Step 1: Generating 30 participant profiles with baseline profiles...")
    participants = generate_participant_profiles(seed=RANDOM_SEED)
    participants_path = OUTPUT_DIR / "participants.json"
    with open(participants_path, "w", encoding="utf-8") as f:
        json.dump(participants, f, indent=2)
    print(f" -> Saved {len(participants)} participant profiles to {participants_path.name}")

    # 2. Generate sessions
    print("\nStep 2: Simulating 60 physiological sessions across 5 scenarios...")
    sessions_meta: List[Dict[str, Any]] = []
    all_records: List[Dict[str, Any]] = []

    base_start_time = datetime(2026, 11, 20, 8, 0, 0, tzinfo=timezone.utc)
    rng_master = np.random.default_rng(RANDOM_SEED + 100)

    session_counter = 1
    for p_idx, participant in enumerate(participants):
        scenario = participant["assigned_scenario_group"]
        
        for s_idx in range(SESSIONS_PER_PARTICIPANT):
            session_seed = int(rng_master.integers(1000, 999999))
            # Offset start times by days and hours for realism
            session_start = base_start_time + timedelta(days=p_idx, hours=s_idx * 4)

            meta, records = simulate_session_timeseries(
                participant=participant,
                session_index=session_counter,
                scenario=scenario,
                start_time=session_start,
                session_seed=session_seed,
            )

            sessions_meta.append(meta)
            all_records.extend(records)
            print(f"  [{session_counter:02d}/{TOTAL_SESSIONS}] {meta['session_id']}: {meta['participant_id']} | {scenario:<28} | Valid: {meta['valid_observations']}/{meta['total_observations']} ({meta['missing_rate_pct']}%) | Mean HR: {meta['hr_mean']} bpm | RMSSD: {meta['empirical_rmssd_ms']} ms")
            session_counter += 1

    # Save sessions metadata
    sessions_path = OUTPUT_DIR / "sessions.json"
    with open(sessions_path, "w", encoding="utf-8") as f:
        json.dump(sessions_meta, f, indent=2)
    print(f"\n -> Saved {len(sessions_meta)} session metadata records to {sessions_path.name}")

    # 3. Export datasets
    print(f"\nStep 3: Exporting full dataset ({len(all_records)} records)...")

    # A. CSV
    csv_path = OUTPUT_DIR / "synthetic_physiological_dataset.csv"
    fieldnames = [
        "timestamp", "participant_id", "session_id", "scenario",
        "heart_rate", "rr_interval", "spo2", "skin_temperature",
        "activity_level", "steps", "accel_x", "accel_y", "accel_z",
        "battery_level", "mission_phase", "external_g_load", "flight_duration_sec",
        "data_source", "dataset_id", "is_synthetic"
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_records:
            row = dict(r)
            if isinstance(row["rr_interval"], list):
                row["rr_interval"] = ";".join(str(x) for x in row["rr_interval"])
            writer.writerow(row)
    csv_size_mb = csv_path.stat().st_size / (1024 * 1024)
    print(f" -> Saved CSV:   {csv_path.name} ({csv_size_mb:.2f} MB)")

    # B. JSONL
    jsonl_path = OUTPUT_DIR / "synthetic_physiological_dataset.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r) + "\n")
    jsonl_size_mb = jsonl_path.stat().st_size / (1024 * 1024)
    print(f" -> Saved JSONL: {jsonl_path.name} ({jsonl_size_mb:.2f} MB)")

    # C. JSON
    json_path = OUTPUT_DIR / "synthetic_physiological_dataset.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f)
    json_size_mb = json_path.stat().st_size / (1024 * 1024)
    print(f" -> Saved JSON:  {json_path.name} ({json_size_mb:.2f} MB)")

    # 4. Generate Dataset Manifest
    print("\nStep 4: Calculating file hashes and generating dataset manifest...")
    import hashlib

    def get_sha256(filepath: Path) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as bf:
            while chunk := bf.read(65536):
                h.update(chunk)
        return h.hexdigest()

    manifest = {
        "dataset_name": "AeroVital Synthetic Physiological Dataset v1",
        "dataset_id": DATASET_ID,
        "generator_version": GENERATOR_VERSION,
        "schema_version": SCHEMA_VERSION,
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "sampling_rate_hz": NOMINAL_SAMPLING_HZ,
        "total_records": len(all_records),
        "total_participants": len(participants),
        "total_sessions": len(sessions_meta),
        "session_duration_sec": SESSION_DURATION_SEC,
        "scenarios": SCENARIO_NAMES,
        "files": {
            "synthetic_physiological_dataset.csv": {
                "size_bytes": csv_path.stat().st_size,
                "sha256": get_sha256(csv_path)
            },
            "synthetic_physiological_dataset.jsonl": {
                "size_bytes": jsonl_path.stat().st_size,
                "sha256": get_sha256(jsonl_path)
            },
            "synthetic_physiological_dataset.json": {
                "size_bytes": json_path.stat().st_size,
                "sha256": get_sha256(json_path)
            },
            "participants.json": {
                "size_bytes": participants_path.stat().st_size,
                "sha256": get_sha256(participants_path)
            },
            "sessions.json": {
                "size_bytes": sessions_path.stat().st_size,
                "sha256": get_sha256(sessions_path)
            }
        },
        "operational_isolation_statement": (
            "This dataset contains solely mathematically modeled synthetic physiological observations. "
            "It is completely isolated from production operational telemetry, real pilot baselines, and "
            "clinical records. Hardware channels not provided by the Wear OS acquisition layer (ECG, SpO2, "
            "skin temperature) are strictly represented as null."
        )
    }

    manifest_path = OUTPUT_DIR / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f" -> Saved Manifest: {manifest_path.name}")

    print(f"\n[SUCCESS] Dataset generation complete! Total observations: {len(all_records):,}")


if __name__ == "__main__":
    main()
