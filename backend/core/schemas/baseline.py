"""Pilot Baseline Schema for AeroVital.

Represents an individual pilot's versioned physiological baseline.
AeroVital requires pilot-specific, versioned baselines. If a baseline is unavailable,
the engine explicitly treats baseline evidence as absent rather than substituting
arbitrary population defaults.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class PilotBaseline(BaseModel):
    """Pilot-specific physiological baseline profile.
    
    A versioned baseline established during controlled resting/pre-flight calibration.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    pilot_id: str = Field(
        ...,
        description="Unique identifier of the pilot."
    )
    baseline_version: str = Field(
        ...,
        description="Version or date identifier of this calibration profile (e.g., '2026-v1.0')."
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when this baseline calibration was recorded."
    )
    resting_heart_rate: float = Field(
        ...,
        description="Calibrated resting heart rate in BPM."
    )
    baseline_rmssd: Optional[float] = Field(
        default=None,
        description="Calibrated baseline RMSSD in milliseconds."
    )
    baseline_sdnn: Optional[float] = Field(
        default=None,
        description="Calibrated baseline SDNN in milliseconds."
    )
    baseline_mean_rr: Optional[float] = Field(
        default=None,
        description="Calibrated baseline mean RR interval in milliseconds."
    )
    calibration_duration_sec: Optional[float] = Field(
        default=None,
        description="Duration of the calibration session in seconds."
    )
    is_calibrated: bool = Field(
        default=True,
        description="Flag indicating if calibration protocol completed successfully."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Calibration context (e.g. ambient temp, resting posture, calibration device)."
    )
