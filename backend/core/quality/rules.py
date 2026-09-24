"""Engineering Signal Quality Rules for AeroVital Core.

Defines configurable rules and metrics for signal quality assessment:
- Completeness and missing sample ratios
- Timestamp continuity and sampling jitter
- Accelerometer-derived motion corruption indicators
- Channel availability differentiation

IMPORTANT: All default thresholds below represent configurable engineering
placeholders for prototype testing. They are NOT medically validated,
clinical, or aviation-certified quality cutoffs.
"""

from datetime import datetime
from enum import Enum
import math
from typing import Dict, List, Optional, Sequence, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field

from backend.core.schemas.telemetry import TelemetrySample


class AccelUnit(str, Enum):
    """Explicit measurement unit contract for accelerometer telemetry."""
    G = "g"
    M_S2 = "m/s2"
    UNSPECIFIED = "unspecified"


class QualityConfig(BaseModel):
    """Configurable engineering rules and thresholds for signal quality assessment.
    
    IMPORTANT: All parameters below represent configurable prototype engineering
    placeholders. None represent clinically, empirically, or operationally validated limits.
    """
    model_config = ConfigDict(frozen=True)

    # Accelerometer unit contract (must be explicitly declared by adapter)
    accel_unit: AccelUnit = Field(
        default=AccelUnit.UNSPECIFIED,
        description="Explicit measurement unit of the accelerometer stream ('g', 'm/s2', or 'unspecified'). Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )

    # Sampling continuity placeholders
    expected_sampling_interval_sec: float = Field(
        default=1.0,
        description="Nominal expected interval between successive telemetry observations in seconds. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    max_acceptable_jitter_sec: float = Field(
        default=0.3,
        description="Threshold for standard deviation of sampling interval before timing quality degrades. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    gap_multiplier_for_missingness: float = Field(
        default=1.8,
        description="Multiple of expected interval beyond which an interval is considered a dropped packet. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )

    # Accelerometer / motion corruption placeholders
    motion_dynamic_accel_threshold: float = Field(
        default=0.35,
        description="Dynamic acceleration magnitude (in g-equivalents) beyond which motion artifacts are flagged. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    motion_severe_accel_threshold: float = Field(
        default=1.20,
        description="Dynamic acceleration magnitude (in g-equivalents) considered severe motion corruption. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )

    # Single-sample motion penalty coefficients
    single_sample_motion_penalty_hr: float = Field(
        default=0.45,
        description="Motion penalty coefficient on single-sample HR SQI. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    single_sample_motion_penalty_rr: float = Field(
        default=0.65,
        description="Motion penalty coefficient on single-sample RR SQI. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    single_sample_motion_penalty_spo2: float = Field(
        default=0.70,
        description="Motion penalty coefficient on single-sample SpO2 SQI. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )

    # Window motion susceptibility coefficients
    window_motion_susceptibility_hr: float = Field(
        default=0.50,
        description="Motion susceptibility weight for windowed HR SQI. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    window_motion_susceptibility_rr: float = Field(
        default=0.70,
        description="Motion susceptibility weight for windowed RR SQI. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    window_motion_susceptibility_spo2: float = Field(
        default=0.80,
        description="Motion susceptibility weight for windowed SpO2 SQI. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )

    # Window presence vs. timing weighting split
    presence_weight: float = Field(
        default=0.50,
        description="Weight allocated to sample presence ratio in window base score. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    timing_weight: float = Field(
        default=0.50,
        description="Weight allocated to timing continuity in window base score. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )

    # Minimum history requirements & cap
    min_history_samples: int = Field(
        default=5,
        description="Minimum number of samples in a window required before a channel can transition out of INSUFFICIENT_HISTORY. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    insufficient_history_penalty_cap: float = Field(
        default=0.40,
        description="Maximum SQI score assigned to a channel with insufficient history. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )

    # Usability cutoffs
    min_channel_sqi_usable: float = Field(
        default=0.40,
        description="Threshold below which a channel is marked unusable (is_usable=False). Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    min_overall_sqi_acceptable: float = Field(
        default=0.40,
        description="Threshold for is_telemetry_acceptable in QualityAssessment. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )

    # Channel weighting for composite SQI calculation
    channel_weights: Dict[str, float] = Field(
        default={
            "heart_rate": 0.40,
            "rr_interval": 0.35,
            "accelerometer": 0.15,
            "spo2": 0.05,
            "skin_temperature": 0.05,
        },
        description="Relative weights for synthesizing overall SQI across active channels. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )


def compute_dynamic_acceleration(
    accel_x: float,
    accel_y: float,
    accel_z: float,
    unit: Union[AccelUnit, str] = AccelUnit.G,
) -> Optional[float]:
    """Compute dynamic (non-gravitational) acceleration magnitude in g-equivalents.
    
    IMPORTANT: Requires an explicit unit contract ('g' or 'm/s2'). Does NOT infer units
    from signal magnitude. If unit is UNSPECIFIED, returns None to avoid silent guessing.
    """
    unit_val = unit.value if isinstance(unit, AccelUnit) else str(unit).lower()
    total_magnitude = math.sqrt(accel_x**2 + accel_y**2 + accel_z**2)

    if unit_val == "g":
        return abs(total_magnitude - 1.0)
    elif unit_val in ("m/s2", "m/s^2", "mps2"):
        # Convert m/s² dynamic deviation to g-equivalent (standard gravity = 9.80665 m/s²)
        return abs(total_magnitude - 9.80665) / 9.80665
    else:
        # Unspecified unit; do not guess
        return None


def evaluate_motion_corruption(
    sample: TelemetrySample,
    config: QualityConfig,
) -> Tuple[float, bool]:
    """Calculate motion corruption index [0.0, 1.0] and motion artifact flag for a single sample.
    
    Returns:
        (motion_corruption_index, motion_artifact_detected)
    """
    if not sample.has_acceleration():
        # Inertial sensor not present; cannot evaluate motion corruption
        return 0.0, False

    dyn_accel = compute_dynamic_acceleration(
        sample.accel_x,  # type: ignore
        sample.accel_y,  # type: ignore
        sample.accel_z,  # type: ignore
        unit=config.accel_unit,
    )
    if dyn_accel is None:
        # Accelerometer unit is unspecified; do not silently guess
        return 0.0, False

    # Scale dynamic acceleration into [0.0, 1.0]
    scaled = min(1.0, dyn_accel / config.motion_severe_accel_threshold)
    artifact_detected = dyn_accel >= config.motion_dynamic_accel_threshold

    return round(scaled, 4), artifact_detected


def evaluate_window_motion(
    samples: Sequence[TelemetrySample],
    config: QualityConfig,
) -> Tuple[float, bool]:
    """Calculate motion corruption index across a sequence of samples.
    
    Combines mean dynamic acceleration and acceleration variance to detect
    both sustained movement and oscillatory inertial movement.
    """
    accel_samples = [s for s in samples if s.has_acceleration()]
    if not accel_samples:
        return 0.0, False

    unit_val = config.accel_unit.value if isinstance(config.accel_unit, AccelUnit) else str(config.accel_unit).lower()
    if unit_val not in ("g", "m/s2", "m/s^2", "mps2"):
        # Unspecified unit; do not silently guess
        return 0.0, False

    scale_to_g = 1.0 if unit_val == "g" else 9.80665

    dyn_accels = [
        compute_dynamic_acceleration(s.accel_x, s.accel_y, s.accel_z, unit=config.accel_unit)  # type: ignore
        for s in accel_samples
    ]
    valid_dyns = [d for d in dyn_accels if d is not None]
    if not valid_dyns:
        return 0.0, False
    mean_dyn = sum(valid_dyns) / len(valid_dyns)

    magnitudes = [
        math.sqrt(s.accel_x**2 + s.accel_y**2 + s.accel_z**2)  # type: ignore
        for s in accel_samples
    ]
    mean_mag = sum(magnitudes) / len(magnitudes)
    std_mag = math.sqrt(sum((m - mean_mag)**2 for m in magnitudes) / len(magnitudes))
    norm_std = std_mag / scale_to_g

    # Combined motion reflects whichever is higher: sustained dynamic acceleration or oscillation
    combined_motion = max(mean_dyn, norm_std)
    motion_index = min(1.0, combined_motion / config.motion_severe_accel_threshold)
    artifact_detected = combined_motion >= config.motion_dynamic_accel_threshold

    return round(motion_index, 4), artifact_detected


def evaluate_sampling_continuity(
    timestamps: Sequence[datetime],
    config: QualityConfig,
) -> Tuple[float, float, float]:
    """Evaluate timestamp continuity, interval jitter, and missing sample ratio.
    
    Returns:
        (timing_sqi, interval_jitter_sec, missing_sample_ratio)
    """
    if len(timestamps) < 2:
        return 1.0, 0.0, 0.0

    deltas = [
        (timestamps[i] - timestamps[i - 1]).total_seconds()
        for i in range(1, len(timestamps))
    ]

    expected = config.expected_sampling_interval_sec
    mean_delta = sum(deltas) / len(deltas)
    variance_delta = sum((d - mean_delta)**2 for d in deltas) / len(deltas)
    jitter = math.sqrt(variance_delta)

    # Count estimated missing samples from gaps
    gap_threshold = expected * config.gap_multiplier_for_missingness
    total_expected_samples = max(1, round((timestamps[-1] - timestamps[0]).total_seconds() / expected) + 1)
    actual_samples = len(timestamps)
    missing_count = max(0, total_expected_samples - actual_samples)
    missing_ratio = min(1.0, missing_count / total_expected_samples)

    # Timing SQI penalizes high jitter and large gaps
    jitter_penalty = min(1.0, jitter / max(0.01, config.max_acceptable_jitter_sec * 2.0))
    timing_sqi = max(0.0, 1.0 - (0.5 * missing_ratio + 0.5 * jitter_penalty))

    return round(timing_sqi, 4), round(jitter, 4), round(missing_ratio, 4)
