"""AeroVital Signal Quality Assessment Layer.

Exports SignalQualityAssessor, QualityConfig, and rule evaluators.
"""

from backend.core.quality.rules import (
    AccelUnit,
    QualityConfig,
    evaluate_motion_corruption,
    evaluate_window_motion,
    evaluate_sampling_continuity,
    compute_dynamic_acceleration,
)
from backend.core.quality.assessment import SignalQualityAssessor

__all__ = [
    "AccelUnit",
    "QualityConfig",
    "SignalQualityAssessor",
    "evaluate_motion_corruption",
    "evaluate_window_motion",
    "evaluate_sampling_continuity",
    "compute_dynamic_acceleration",
]
