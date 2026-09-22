"""Operational & Environmental Context Schema for AeroVital.

Separates operational flight conditions and avionics data from raw wearable telemetry.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class MissionPhase(str, Enum):
    """Operational flight phases."""
    PRE_FLIGHT = "PRE_FLIGHT"
    TAXI = "TAXI"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    COMBAT_MANEUVER = "COMBAT_MANEUVER"
    HIGH_G = "HIGH_G"
    DESCENT = "DESCENT"
    APPROACH = "APPROACH"
    LANDING = "LANDING"
    POST_FLIGHT = "POST_FLIGHT"
    EMERGENCY = "EMERGENCY"
    UNKNOWN = "UNKNOWN"


class OperationalContext(BaseModel):
    """Contextual flight environment information.
    
    Provided alongside physiological telemetry to prevent misinterpreting 
    high workload/maneuvers as baseline fatigue.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(
        ...,
        description="UTC timestamp corresponding to the operational observation."
    )
    mission_phase: Optional[MissionPhase] = Field(
        default=None,
        description="Current operational flight phase."
    )
    external_g_load: Optional[float] = Field(
        default=None,
        description="Airframe G-force reported by aircraft avionics / accelerometer."
    )
    flight_duration_sec: Optional[float] = Field(
        default=None,
        description="Total elapsed flight duration in seconds from engine start or takeoff."
    )
    altitude_feet: Optional[float] = Field(
        default=None,
        description="Flight altitude in feet above sea level."
    )
    cabin_pressure_altitude_feet: Optional[float] = Field(
        default=None,
        description="Cockpit cabin altitude equivalent in feet."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional operational or environmental telemetry key-values."
    )
