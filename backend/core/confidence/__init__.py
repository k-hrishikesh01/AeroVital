"""Confidence Evaluation & Result Generation Layer for AeroVital Core.

Provides:
- ConfidenceConfig: Prototype weights and thresholds for confidence calculation.
- ConfidenceBreakdown: Multi-dimensional audit container for confidence scores.
- ConfidenceEvaluator: Step 8 confidence assessment and result assembly engine.
"""

from backend.core.confidence.config import ConfidenceConfig
from backend.core.confidence.evaluator import (
    ConfidenceBreakdown,
    ConfidenceEvaluator,
)

__all__ = [
    "ConfidenceConfig",
    "ConfidenceBreakdown",
    "ConfidenceEvaluator",
]
