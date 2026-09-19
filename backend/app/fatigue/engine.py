from backend.app.core.models import TelemetryData, FatigueResult, FatigueState, MissionPhase
from pydantic import BaseModel
from typing import List, Optional
import datetime

class FatigueConfig(BaseModel):
    baseline_hr: float = 70.0
    baseline_hrv_rmssd: float = 50.0
    
    weight_hr_deviation: float = 0.3
    weight_hrv_degradation: float = 0.3
    weight_g_load: float = 0.2
    weight_mission_phase: float = 0.2
    
    smoothing_factor: float = 0.2  # new_state = (1 - factor) * old_state + factor * current_score

class FatigueEngine:
    def __init__(self, config: Optional[FatigueConfig] = None):
        self.config = config or FatigueConfig()
        self.previous_score = 0.0
        self.session_start_time: Optional[datetime.datetime] = None
        
    def evaluate(self, telemetry: TelemetryData) -> FatigueResult:
        if self.session_start_time is None:
            self.session_start_time = telemetry.timestamp
            
        factors = []
        raw_score = 0.0
        
        # 1. HR Deviation / Elevated HR
        if telemetry.heart_rate > self.config.baseline_hr:
            hr_penalty = min(1.0, (telemetry.heart_rate - self.config.baseline_hr) / 100.0)
            raw_score += hr_penalty * self.config.weight_hr_deviation
            if hr_penalty > 0.3:
                factors.append("Elevated Heart Rate")
                
        # 2. HRV Degradation
        if telemetry.hrv_rmssd is not None and telemetry.hrv_rmssd < self.config.baseline_hrv_rmssd:
            hrv_penalty = min(1.0, (self.config.baseline_hrv_rmssd - telemetry.hrv_rmssd) / self.config.baseline_hrv_rmssd)
            raw_score += hrv_penalty * self.config.weight_hrv_degradation
            if hrv_penalty > 0.3:
                factors.append("HRV Degradation")
                
        # 3. G-load / Context
        if telemetry.g_load is not None and telemetry.g_load > 1.5:
            g_penalty = min(1.0, (telemetry.g_load - 1.0) / 8.0) # max G roughly 9
            raw_score += g_penalty * self.config.weight_g_load
            if g_penalty > 0.3:
                factors.append("High G-Load")
                
        # 4. Mission Duration / Phase
        phase_penalty = 0.0
        if telemetry.mission_phase in [MissionPhase.HIGH_G, MissionPhase.EMERGENCY, MissionPhase.LANDING]:
            phase_penalty = 0.8
        elif telemetry.mission_phase in [MissionPhase.TAKEOFF, MissionPhase.RECOVERY]:
            phase_penalty = 0.5
        
        raw_score += phase_penalty * self.config.weight_mission_phase
        if phase_penalty > 0.5:
            factors.append(f"Phase: {telemetry.mission_phase.value}")
            
        # 5. Mission Duration
        duration_seconds = (telemetry.timestamp - self.session_start_time).total_seconds()
        duration_penalty = min(0.2, duration_seconds / (4 * 3600)) # up to 0.2 penalty for 4 hours
        raw_score += duration_penalty
        
        # Cap score at 1.0
        raw_score = min(1.0, max(0.0, raw_score))
        
        # Temporal smoothing (hysteresis)
        smoothed_score = (self.previous_score * (1.0 - self.config.smoothing_factor) +
                          raw_score * self.config.smoothing_factor)
        
        self.previous_score = smoothed_score
        
        # Determine state
        state = FatigueState.NORMAL
        if smoothed_score > 0.7:
            state = FatigueState.FATIGUE
        elif smoothed_score > 0.4:
            state = FatigueState.ELEVATED_WORKLOAD
            
        # Confidence logic (simple for now)
        missing_vars = sum([
            1 for x in [telemetry.hrv_rmssd, telemetry.g_load, telemetry.mission_phase] if x is None
        ])
        confidence = max(0.0, 1.0 - (missing_vars * 0.2))
        
        if not factors and smoothed_score > 0.2:
            factors.append("Duration / Baseline Accumulation")
            
        return FatigueResult(
            timestamp=telemetry.timestamp,
            fatigue_score=smoothed_score,
            fatigue_state=state,
            confidence=confidence,
            dominant_factors=factors[:3]  # top 3 factors
        )
