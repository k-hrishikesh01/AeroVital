"""Provisional Rule-Based Estimator for AeroVital Intelligence.

Implements ProvisionalRuleBasedEstimator: a stateless, pure inference service that
evaluates descriptive features, baseline comparisons, and operational context to produce
a candidate operational state.

STRICT PRINCIPLES:
1. Pure function: FeatureVector, OperationalContext, and QualityAssessment are never mutated.
2. Step 7 owns state inference; Step 8 owns confidence and final abstention gating.
3. Missing inputs are never defaulted (no-imputation contract).
4. Option B: provisional_score is strictly None.
"""

from typing import Optional

from backend.core.schemas.context import OperationalContext
from backend.core.schemas.features import FeatureVector
from backend.core.schemas.quality import QualityAssessment
from backend.core.intelligence.config import EstimatorConfig
from backend.core.intelligence.rules import (
    ProvisionalEstimationOutput,
    evaluate_state_rules,
)


class ProvisionalRuleBasedEstimator:
    """Deterministic, pure rule-based state estimator for AeroVital Core."""

    def __init__(self, config: Optional[EstimatorConfig] = None):
        self.config = config or EstimatorConfig()

    def evaluate(
        self,
        features: FeatureVector,
        context: Optional[OperationalContext] = None,
        quality: Optional[QualityAssessment] = None,
        baseline_version: Optional[str] = None,
    ) -> ProvisionalEstimationOutput:
        """Evaluate evidence to determine candidate operational state.
        
        Args:
            features: FeatureVector with descriptive and baseline comparison metrics.
            context: Optional flight context (G-load, phase, duration). Never defaulted.
            quality: Optional quality assessment for channel screening.
            baseline_version: Provenance version ID of the pilot baseline, if available.
            
        Returns:
            ProvisionalEstimationOutput with candidate_state, dominant_factors, and audit trace.
        """
        return evaluate_state_rules(
            features=features,
            context=context,
            quality=quality,
            config=self.config,
            baseline_version=baseline_version,
        )
