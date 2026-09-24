"""Standardized Telemetry Schema for AeroVital.

Preserves the backend-facing telemetry contract while ensuring sensor-agnostic,
framework-independent representation. Optional channels remain optional so the
engine can operate seamlessly on whatever subset is provided by the connected wearable.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class TelemetrySample(BaseModel):
    """Standardized physiological and motion telemetry sample.
    
    Fields mirror the backend-facing contract. Non-essential channels are optional
    to support diverse wearable capabilities.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(
        ...,
        description="UTC timestamp of the telemetry observation."
    )
    heart_rate: Optional[float] = Field(
        default=None,
        description="Heart rate in beats per minute (BPM)."
    )
    rr_interval: Optional[Union[float, List[float]]] = Field(
        default=None,
        description="Inter-beat interval(s) in milliseconds (RR / IBI). Accepts single float or list."
    )
    spo2: Optional[float] = Field(
        default=None,
        description="Blood oxygen saturation percentage (0 - 100%)."
    )
    skin_temperature: Optional[float] = Field(
        default=None,
        description="Skin temperature in degrees Celsius."
    )
    activity_level: Optional[Union[str, float]] = Field(
        default=None,
        description="Wearable-reported activity classification or continuous activity metric."
    )
    steps: Optional[int] = Field(
        default=None,
        description="Step count reported by wearable pedometer."
    )
    accel_x: Optional[float] = Field(
        default=None,
        description="X-axis acceleration (m/s² or g-force, vendor-agnostic)."
    )
    accel_y: Optional[float] = Field(
        default=None,
        description="Y-axis acceleration (m/s² or g-force, vendor-agnostic)."
    )
    accel_z: Optional[float] = Field(
        default=None,
        description="Z-axis acceleration (m/s² or g-force, vendor-agnostic)."
    )
    battery_level: Optional[float] = Field(
        default=None,
        description="Device battery percentage (0 - 100%)."
    )
    raw_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional vendor-specific metadata or raw sensor diagnostic dictionary."
    )

    def get_rr_intervals(self) -> List[float]:
        """Normalize rr_interval into a clean list of floats."""
        if self.rr_interval is None:
            return []
        if isinstance(self.rr_interval, (int, float)):
            return [float(self.rr_interval)]
        return [float(x) for x in self.rr_interval]

    def has_acceleration(self) -> bool:
        """Check whether 3-axis accelerometer readings are present."""
        return self.accel_x is not None and self.accel_y is not None and self.accel_z is not None
