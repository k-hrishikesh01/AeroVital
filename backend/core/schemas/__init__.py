"""AeroVital Core Schemas.

Public contract definitions for telemetry, context, baselines, quality,
features, and fatigue results.
"""

from backend.core.schemas.telemetry import TelemetrySample
from backend.core.schemas.context import MissionPhase, OperationalContext
from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.quality import ChannelQuality, QualityAssessment
from backend.core.schemas.features import (
    HeartRateFeatures,
    HRVFeatures,
    MotionFeatures,
    BaselineComparisonFeatures,
    FeatureVector,
)
from backend.core.schemas.result import (
    FatigueState,
    EstimationMetadata,
    FatigueEstimationResult,
)

__all__ = [
    "TelemetrySample",
    "MissionPhase",
    "OperationalContext",
    "PilotBaseline",
    "ChannelQuality",
    "QualityAssessment",
    "HeartRateFeatures",
    "HRVFeatures",
    "MotionFeatures",
    "BaselineComparisonFeatures",
    "FeatureVector",
    "FatigueState",
    "EstimationMetadata",
    "FatigueEstimationResult",
]
