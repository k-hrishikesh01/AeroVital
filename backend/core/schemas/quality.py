"""Signal Quality Assessment Schema for AeroVital.

Provides per-channel and aggregate Signal Quality Index (SQI) records,
identifying missing samples, physiological plausibility, and motion corruption.
"""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChannelQuality(BaseModel):
    """Quality metrics for a single physiological or sensor channel."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    channel_name: str = Field(
        ...,
        description="Name of the channel (e.g. 'heart_rate', 'rr_interval', 'accelerometer')."
    )
    sqi_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Signal Quality Index score between 0.0 (unusable) and 1.0 (pristine)."
    )
    is_usable: bool = Field(
        ...,
        description="Whether this channel contains sufficient valid signal for feature extraction."
    )
    missing_sample_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Proportion of missing or dropped readings in the evaluation window."
    )
    motion_artifact_detected: bool = Field(
        default=False,
        description="True if sensor movement corruption exceeded threshold during observation."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Diagnostic information or error flags."
    )


class QualityAssessment(BaseModel):
    """Overall multi-channel signal quality evaluation."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(
        ...,
        description="UTC timestamp of the assessment."
    )
    overall_sqi: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite signal quality score between 0.0 and 1.0."
    )
    channels: Dict[str, ChannelQuality] = Field(
        default_factory=dict,
        description="Channel-specific quality breakdown."
    )
    motion_corruption_index: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Magnitude of inertial motion interference (0.0=still, 1.0=severe)."
    )
    is_telemetry_acceptable: bool = Field(
        default=True,
        description="Whether aggregate quality is sufficient to attempt state estimation."
    )

    def get_channel_sqi(self, channel_name: str) -> Optional[float]:
        """Convenience method to retrieve a specific channel's SQI score."""
        ch = self.channels.get(channel_name)
        return ch.sqi_score if ch else None
