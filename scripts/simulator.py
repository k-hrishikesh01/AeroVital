import time
import requests
import random
import math
from datetime import datetime, timezone
import argparse

# Configuration
API_URL = "http://127.0.0.1:8000/api/v1/telemetry"

PHASES = ["TAXI", "TAKEOFF", "CLIMB", "CRUISE", "HIGH_G", "RECOVERY", "LANDING"]

def generate_telemetry_loop(duration_minutes=10, interval_seconds=1):
    start_time = time.time()
    end_time = start_time + duration_minutes * 60
    
    # Baselines
    hr_base = 70.0
    hrv_base = 50.0
    spo2_base = 98.0
    resp_base = 14.0
    temp_base = 36.5
    
    # State tracking
    fatigue_accumulation = 0.0
    current_phase_idx = 0
    phase_duration = (duration_minutes * 60) / len(PHASES)
    
    print(f"Starting simulation for {duration_minutes} minutes, sending data every {interval_seconds}s...")
    
    while time.time() < end_time:
        elapsed = time.time() - start_time
        current_phase = PHASES[min(int(elapsed / phase_duration), len(PHASES)-1)]
        
        # Accumulate fatigue slowly over time
        fatigue_accumulation += (interval_seconds / 3600.0) * 0.1 # Very slow base accumulation
        
        # Phase-specific effects
        hr_modifier = 0
        hrv_modifier = 0
        g_load = 1.0
        
        if current_phase == "TAXI":
            hr_modifier = 5
        elif current_phase == "TAKEOFF":
            hr_modifier = 25
            hrv_modifier = -10
            g_load = 1.2 + random.uniform(0, 0.2)
        elif current_phase == "CLIMB":
            hr_modifier = 15
            hrv_modifier = -5
            g_load = 1.1
        elif current_phase == "CRUISE":
            hr_modifier = 5
            hrv_modifier = 0
            g_load = 1.0 + random.uniform(-0.05, 0.05)
            # Recovery during cruise
            fatigue_accumulation = max(0.0, fatigue_accumulation - 0.0001)
        elif current_phase == "HIGH_G":
            hr_modifier = 40
            hrv_modifier = -25
            g_load = 3.0 + math.sin(elapsed / 2.0) * 2.0 + random.uniform(-0.5, 0.5)
            fatigue_accumulation += 0.005 # Rapid accumulation
        elif current_phase == "RECOVERY":
            hr_modifier = 10
            hrv_modifier = -5
            g_load = 1.0
        elif current_phase == "LANDING":
            hr_modifier = 20
            hrv_modifier = -15
            g_load = 1.1 + random.uniform(0, 0.2)
            
        # Add noise and fatigue effects
        noise = random.uniform(-2, 2)
        fatigue_hr_effect = fatigue_accumulation * 20
        fatigue_hrv_effect = fatigue_accumulation * 15
        
        current_hr = hr_base + hr_modifier + fatigue_hr_effect + noise + math.sin(elapsed/10.0)*5
        current_hrv = max(5.0, hrv_base + hrv_modifier - fatigue_hrv_effect + random.uniform(-3, 3))
        current_spo2 = max(90.0, min(100.0, spo2_base - (fatigue_accumulation * 5) + random.uniform(-1, 1)))
        current_resp = max(10.0, resp_base + (current_hr - hr_base)/10.0 + random.uniform(-1, 1))
        current_temp = temp_base + fatigue_accumulation + random.uniform(-0.1, 0.1)
        
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": round(current_hr, 1),
            "hrv_rmssd": round(current_hrv, 1),
            "hrv_sdnn": round(current_hrv * 1.2, 1), # just a proxy
            "spo2": round(current_spo2, 1),
            "respiratory_rate": round(current_resp, 1),
            "skin_temperature": round(current_temp, 2),
            "g_load": round(g_load, 2),
            "mission_phase": current_phase
        }
        
        try:
            resp = requests.post(API_URL, json=data)
            if resp.status_code == 200:
                result = resp.json()
                print(f"[{current_phase}] HR: {data['heart_rate']} G: {data['g_load']} -> State: {result['fatigue_state']} (Score: {result['fatigue_score']:.2f})")
            else:
                print(f"Failed to send telemetry: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"Error sending telemetry: {e}")
            
        time.sleep(interval_seconds)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AeroVital Synthetic Telemetry Generator")
    parser.add_argument("--duration", type=int, default=10, help="Duration in minutes")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval in seconds")
    args = parser.parse_args()
    
    generate_telemetry_loop(args.duration, args.interval)
