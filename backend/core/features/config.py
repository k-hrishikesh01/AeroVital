"""Configuration models and enums for AeroVital Feature Extraction.

Defines:
- HRTrendUnit: Enumeration of output units for heart rate linear trend slope.
- FeatureConfig: Pydantic configuration centralizing operational minimum sample requirements,
  declared acceleration units, and trend slope unit selection.

IMPORTANT: All operational thresholds are configurable prototype engineering placeholders;
none represent clinically, empirically, or operationally validated cutoffs.
"""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

from backend.core.quality.rules import AccelUnit


class HRTrendUnit(str, Enum):
    """Explicit unit selection for heart rate linear trend slope."""
    BPM_PER_MINUTE = "bpm_per_minute"
    BPM_PER_SECOND = "bpm_per_second"


class FeatureConfig(BaseModel):
    """Configurable engineering parameters for feature extraction.
    
    IMPORTANT: All parameters below represent configurable prototype engineering
    placeholders. None represent clinically, empirically, or operationally validated limits.
    """
    model_config = ConfigDict(frozen=True)

    min_rr_samples_for_hrv: int = Field(
        default=5,
        ge=2,
        description="Operational minimum number of clean RR intervals required to compute HRV features. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    min_consecutive_rr_pairs: int = Field(
        default=3,
        ge=1,
        description="Operational minimum number of genuinely adjacent consecutive RR pairs required for RMSSD and pNN50. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    min_hr_samples_for_dynamics: int = Field(
        default=3,
        ge=1,
        description="Operational minimum number of heart rate samples required to compute HR statistics. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    min_accel_samples_for_motion: int = Field(
        default=3,
        ge=1,
        description="Operational minimum number of complete accelerometer triplets required to compute motion features. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    accel_unit: AccelUnit = Field(
        default=AccelUnit.UNSPECIFIED,
        description="Explicit declared accelerometer unit. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    hr_trend_unit: HRTrendUnit = Field(
        default=HRTrendUnit.BPM_PER_MINUTE,
        description="Explicit output unit configuration for heart rate linear trend slope."
    )
