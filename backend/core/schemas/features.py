"""Extracted Feature Vector Schemas for AeroVital.

Represents physiological, autonomic, inertial, and baseline-comparative features
computed over a temporal observation window.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class HeartRateFeatures(BaseModel):
    """Heart rate dynamics computed over a temporal window."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    mean_hr: Optional[float] = Field(default=None, description="Average heart rate (BPM).")
    min_hr: Optional[float] = Field(default=None, description="Minimum heart rate (BPM).")
    max_hr: Optional[float] = Field(default=None, description="Maximum heart rate (BPM).")
    hr_std: Optional[float] = Field(default=None, description="Standard deviation of heart rate.")
    hr_range: Optional[float] = Field(default=None, description="Difference between maximum and minimum heart rate in window (BPM).")
    hr_trend: Optional[float] = Field(default=None, description="Linear trend slope of HR over window.")


class HRVFeatures(BaseModel):
    """Time-domain Heart Rate Variability (HRV) metrics."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    mean_rr_ms: Optional[float] = Field(default=None, description="Mean of valid RR intervals (ms).")
    sdnn_ms: Optional[float] = Field(default=None, description="Standard deviation of NN intervals (ms).")
    rmssd_ms: Optional[float] = Field(default=None, description="Root mean square of successive differences (ms).")
    pnn50_percent: Optional[float] = Field(default=None, description="Percentage of successive RR differences > 50ms.")
    valid_intervals_count: int = Field(default=0, description="Total count of clean RR intervals in window.")


class MotionFeatures(BaseModel):
    """Inertial metrics computed from accelerometer readings."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    mean_magnitude: Optional[float] = Field(default=None, description="Mean 3-axis accelerometer magnitude.")
    variance_magnitude: Optional[float] = Field(default=None, description="Variance of acceleration magnitude.")
    peak_magnitude: Optional[float] = Field(default=None, description="Peak acceleration magnitude in window.")
    activity_intensity: Optional[float] = Field(default=None, description="Estimated physical activity intensity.")


class BaselineComparisonFeatures(BaseModel):
    """Deviations computed relative to an individual pilot's baseline.
    
    If no pilot baseline is available, baseline_available is False and deviation
    metrics remain None. No population default substitution is permitted.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_available: bool = Field(
        default=False,
        description="True if a valid PilotBaseline was provided for comparison."
    )
    hr_deviation_from_baseline: Optional[float] = Field(
        default=None,
        description="Delta between window mean HR and pilot's calibrated resting HR (BPM)."
    )
    hrv_rmssd_ratio_to_baseline: Optional[float] = Field(
        default=None,
        description="Ratio of window RMSSD to calibrated baseline RMSSD (values < 1.0 indicate degradation)."
    )


class FeatureVector(BaseModel):
    """Unified container for all extracted features over a temporal window."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    window_start: datetime = Field(..., description="Start timestamp of the observation window.")
    window_end: datetime = Field(..., description="End timestamp of the observation window.")
    window_duration_sec: float = Field(..., description="Effective duration of the window in seconds.")
    
    hr_features: HeartRateFeatures = Field(default_factory=HeartRateFeatures)
    hrv_features: HRVFeatures = Field(default_factory=HRVFeatures)
    motion_features: MotionFeatures = Field(default_factory=MotionFeatures)
    baseline_features: BaselineComparisonFeatures = Field(default_factory=BaselineComparisonFeatures)
