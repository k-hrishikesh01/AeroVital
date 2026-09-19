from backend.app.fatigue.engine import FatigueEngine
from backend.app.core.models import TelemetryData, MissionPhase, FatigueState
from datetime import datetime, timezone
import pytest

def test_normal_fatigue_state():
    engine = FatigueEngine()
    telemetry = TelemetryData(
        timestamp=datetime.now(timezone.utc),
        heart_rate=70.0,
        hrv_rmssd=50.0,
        mission_phase=MissionPhase.CRUISE,
        g_load=1.0
    )
    
    result = engine.evaluate(telemetry)
    assert result.fatigue_state == FatigueState.NORMAL
    assert result.fatigue_score < 0.4

def test_high_g_fatigue_state():
    engine = FatigueEngine()
    telemetry = TelemetryData(
        timestamp=datetime.now(timezone.utc),
        heart_rate=140.0,
        hrv_rmssd=20.0,
        mission_phase=MissionPhase.HIGH_G,
        g_load=6.0
    )
    
    # Needs a few iterations due to smoothing
    for _ in range(10):
        result = engine.evaluate(telemetry)
        
    assert result.fatigue_state in [FatigueState.ELEVATED_WORKLOAD, FatigueState.FATIGUE]
    assert result.fatigue_score > 0.4
