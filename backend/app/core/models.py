from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from datetime import datetime

class MissionPhase(str, Enum):
    TAXI = "TAXI"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    HIGH_G = "HIGH_G"
    RECOVERY = "RECOVERY"
    LANDING = "LANDING"
    EMERGENCY = "EMERGENCY"

class FatigueState(str, Enum):
    NORMAL = "NORMAL"
    ELEVATED_WORKLOAD = "ELEVATED_WORKLOAD"
    FATIGUE = "FATIGUE"

class TelemetryData(BaseModel):
    timestamp: datetime
    heart_rate: float
    hrv_rmssd: Optional[float] = None
    hrv_sdnn: Optional[float] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[float] = None
    skin_temperature: Optional[float] = None
    g_load: Optional[float] = None
    mission_phase: Optional[MissionPhase] = None

class FatigueResult(BaseModel):
    timestamp: datetime
    fatigue_score: float
    fatigue_state: FatigueState
    confidence: float
    dominant_factors: List[str]
