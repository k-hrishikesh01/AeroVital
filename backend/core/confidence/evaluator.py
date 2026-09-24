"""Confidence Evaluation & Final Result Generation for AeroVital.

Implements ConfidenceEvaluator: evaluates multi-dimensional evidence confidence,
enforces the global telemetry quality gate and confidence abstention gate,
and produces the definitive FatigueEstimationResult.

STRICT PRINCIPLES:
1. Confidence C(t) is bounded in [0.0, 1.0] and deterministic.
2. Global telemetry gate: unacceptable telemetry forces INSUFFICIENT_DATA.
3. Confidence gate: confidence below threshold forces INSUFFICIENT_DATA.
4. Step 7 INSUFFICIENT_DATA is strictly preserved (no recovery).
5. Option B: fatigue_score is strictly None.
6. Pure function: no input mutations, no side effects, framework-independent.
7. Zero hidden state estimation: Step 8 evaluates evidence quality, never physiological thresholds.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.core.schemas.context import OperationalContext
from backend.core.schemas.features import FeatureVector
from backend.core.schemas.quality import QualityAssessment
from backend.core.schemas.result import (
    EstimationMetadata,
    FatigueEstimationResult,
    FatigueState,
)
from backend.core.intelligence.rules import ProvisionalEstimationOutput
from backend.core.confidence.config import ConfidenceConfig

# Number of distinct confirmed evidence items required for full candidate completeness
COMPLETENESS_ITEMS_COUNT = 4.0
EVIDENCE_ITEM_INCREMENT = 1.0 / COMPLETENESS_ITEMS_COUNT


class ConfidenceBreakdown(BaseModel):
    """Detailed audit container of confidence evaluation dimensions."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    global_sqi_score: float = Field(..., ge=0.0, le=1.0, description="Score component derived from overall SQI.")
    channel_quality_score: float = Field(..., ge=0.0, le=1.0, description="Score component derived from relied-upon channels.")
    evidence_completeness_score: float = Field(..., ge=0.0, le=1.0, description="Score component derived from required evidence completeness.")
    motion_integrity_score: float = Field(..., ge=0.0, le=1.0, description="Score component derived from motion artifact freedom.")
    relied_channels: List[str] = Field(default_factory=list, description="Channels relied upon by the candidate state.")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Synthesized confidence score C(t).")
    is_telemetry_acceptable: bool = Field(..., description="Whether telemetry passed the global SQI gate.")
    is_confidence_acceptable: bool = Field(..., description="Whether overall confidence met the abstention threshold.")


def get_relied_channels(
    candidate_state: FatigueState,
    trace: Dict[str, Any],
) -> List[str]:
    """Identify which physiological/inertial channels are relied upon by the candidate state.
    
    Channels not required by the candidate's Step 7 evidence contract are strictly excluded
    to prevent arbitrary confidence penalties from optional or unused sensors.
    """
    if candidate_state == FatigueState.NORMAL:
        return ["heart_rate", "rr_interval"]
    elif candidate_state == FatigueState.ELEVATED_WORKLOAD:
        channels = ["heart_rate"]
        context_reasons = trace.get("rule_workload", {}).get("context_reasons", [])
        if any("motion" in r.lower() for r in context_reasons):
            channels.append("accelerometer")
        return channels
    elif candidate_state == FatigueState.FATIGUE:
        return ["rr_interval"]
    else:
        # INSUFFICIENT_DATA: consider primary physiological channels
        return ["heart_rate", "rr_interval"]


def compute_channel_quality_score(
    quality: Optional[QualityAssessment],
    relied_channels: List[str],
) -> float:
    """Compute average quality score across channels relied upon by candidate state."""
    if quality is None or not relied_channels:
        return 0.0

    scores: List[float] = []
    for ch_name in relied_channels:
        ch = quality.channels.get(ch_name)
        if ch is None or not ch.is_usable:
            scores.append(0.0)
        else:
            scores.append(ch.sqi_score)

    return sum(scores) / len(scores) if scores else 0.0


def compute_evidence_completeness_score(
    provisional: ProvisionalEstimationOutput,
    features: Optional[FeatureVector] = None,
) -> float:
    """Evaluate completeness of required operands and predicates for candidate state.
    
    Reads directly from Step 7's rule_evidence_trace. Does not award confidence
    merely because a field exists in features, and strictly returns 0.0 if Step 7
    found contradictory or insufficient evidence.
    """
    trace = provisional.rule_evidence_trace
    candidate = provisional.candidate_state

    # Contradicted evidence yields zero completeness
    if trace.get("contradiction_detected", False):
        return 0.0

    if candidate == FatigueState.NORMAL:
        norm_trace = trace.get("rule_normal", {})
        score = 0.0
        if norm_trace.get("hr_concordance_available"):
            score += EVIDENCE_ITEM_INCREMENT
        if norm_trace.get("rmssd_concordance_available"):
            score += EVIDENCE_ITEM_INCREMENT
        if norm_trace.get("physio_concordance_supported"):
            score += EVIDENCE_ITEM_INCREMENT
        if norm_trace.get("context_supported"):
            score += EVIDENCE_ITEM_INCREMENT
        return min(1.0, score)

    elif candidate == FatigueState.ELEVATED_WORKLOAD:
        wl_trace = trace.get("rule_workload", {})
        score = 0.0
        if wl_trace.get("physio_available"):
            score += EVIDENCE_ITEM_INCREMENT
        if wl_trace.get("physio_supported"):
            score += EVIDENCE_ITEM_INCREMENT
        if wl_trace.get("context_available"):
            score += EVIDENCE_ITEM_INCREMENT
        if wl_trace.get("context_supported"):
            score += EVIDENCE_ITEM_INCREMENT
        return min(1.0, score)

    elif candidate == FatigueState.FATIGUE:
        fat_trace = trace.get("rule_fatigue", {})
        score = 0.0
        if fat_trace.get("autonomic_available"):
            score += EVIDENCE_ITEM_INCREMENT
        if fat_trace.get("autonomic_supported"):
            score += EVIDENCE_ITEM_INCREMENT
        if fat_trace.get("benign_context_available"):
            score += EVIDENCE_ITEM_INCREMENT
        if fat_trace.get("context_supported") and not fat_trace.get("contradictory_workload"):
            score += EVIDENCE_ITEM_INCREMENT
        return min(1.0, score)

    else:
        # INSUFFICIENT_DATA: evidence was insufficient or unsupported
        return 0.0


def compute_global_sqi_score(
    quality: Optional[QualityAssessment],
    config: ConfidenceConfig,
) -> float:
    """Evaluate global telemetry quality score component."""
    if quality is None:
        return 0.0
    if not quality.is_telemetry_acceptable or quality.overall_sqi < config.min_overall_sqi:
        return min(quality.overall_sqi, config.unacceptable_telemetry_cap)
    return quality.overall_sqi


def compute_motion_integrity_score(quality: Optional[QualityAssessment]) -> float:
    """Evaluate motion integrity component (freedom from inertial artifacts)."""
    if quality is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - quality.motion_corruption_index))


class ConfidenceEvaluator:
    """Stateless evaluator for confidence assessment and result generation."""

    def __init__(self, config: Optional[ConfidenceConfig] = None):
        self.config = config or ConfidenceConfig()

    def compute_breakdown(
        self,
        provisional: ProvisionalEstimationOutput,
        quality: Optional[QualityAssessment] = None,
        features: Optional[FeatureVector] = None,
        context: Optional[OperationalContext] = None,
    ) -> ConfidenceBreakdown:
        """Compute the multi-dimensional confidence breakdown without assembling final result.
        
        Args:
            provisional: Step 7 provisional candidate output.
            quality: Step 3 signal quality assessment.
            features: Step 5/6 feature vector.
            context: Operational flight context.
            
        Returns:
            ConfidenceBreakdown containing individual component scores and overall confidence.
        """
        cfg = self.config
        trace = provisional.rule_evidence_trace

        # 1. Global SQI score
        global_score = compute_global_sqi_score(quality, cfg)

        # 2. Relied-upon channel quality score
        relied_channels = get_relied_channels(provisional.candidate_state, trace)
        channel_score = compute_channel_quality_score(quality, relied_channels)

        # 3. Evidence completeness score
        completeness_score = compute_evidence_completeness_score(provisional, features)

        # 4. Motion integrity score
        motion_score = compute_motion_integrity_score(quality)

        # Weighted combination
        raw_conf = (
            cfg.weight_global_sqi * global_score
            + cfg.weight_channel_quality * channel_score
            + cfg.weight_evidence_completeness * completeness_score
            + cfg.weight_motion_integrity * motion_score
        )
        overall_confidence = max(0.0, min(1.0, round(raw_conf, 4)))

        # Gating flags
        is_telemetry_acceptable = (
            quality is not None
            and quality.is_telemetry_acceptable
            and quality.overall_sqi >= cfg.min_overall_sqi
        )
        is_confidence_acceptable = overall_confidence >= cfg.confidence_threshold

        return ConfidenceBreakdown(
            global_sqi_score=round(global_score, 4),
            channel_quality_score=round(channel_score, 4),
            evidence_completeness_score=round(completeness_score, 4),
            motion_integrity_score=round(motion_score, 4),
            relied_channels=relied_channels,
            overall_confidence=overall_confidence,
            is_telemetry_acceptable=is_telemetry_acceptable,
            is_confidence_acceptable=is_confidence_acceptable,
        )

    def evaluate(
        self,
        provisional: ProvisionalEstimationOutput,
        quality: Optional[QualityAssessment] = None,
        features: Optional[FeatureVector] = None,
        context: Optional[OperationalContext] = None,
    ) -> FatigueEstimationResult:
        """Evaluate evidence confidence and assemble final FatigueEstimationResult.
        
        Args:
            provisional: Step 7 provisional candidate output.
            quality: Step 3 signal quality assessment.
            features: Step 5/6 feature vector.
            context: Operational flight context.
            
        Returns:
            FatigueEstimationResult with definitive state, confidence, and metadata.
        """
        cfg = self.config
        breakdown = self.compute_breakdown(
            provisional=provisional,
            quality=quality,
            features=features,
            context=context,
        )

        overall_sqi = quality.overall_sqi if quality is not None else 0.0
        confidence = breakdown.overall_confidence

        # Abstention decision pipeline
        if provisional.candidate_state == FatigueState.INSUFFICIENT_DATA:
            # Rule 1: Step 7 INSUFFICIENT_DATA is strictly preserved
            final_state = FatigueState.INSUFFICIENT_DATA
            dominant_factors = list(provisional.dominant_factors)
        elif not breakdown.is_telemetry_acceptable:
            # Rule 2: Global SQI gate failure
            final_state = FatigueState.INSUFFICIENT_DATA
            dominant_factors = [
                f"Telemetry globally unacceptable for state estimation (overall SQI: {overall_sqi:.2f})"
            ] + list(provisional.dominant_factors)
        elif not breakdown.is_confidence_acceptable:
            # Rule 3: Evidence confidence abstention gate failure
            final_state = FatigueState.INSUFFICIENT_DATA
            dominant_factors = [
                f"Estimation confidence inadequate ({confidence:.2f} < threshold {cfg.confidence_threshold:.2f})"
            ] + list(provisional.dominant_factors)
        else:
            # Rule 4: Candidate accepted with adequate confidence and quality
            final_state = provisional.candidate_state
            dominant_factors = list(provisional.dominant_factors)

        metadata = EstimationMetadata(
            estimator_id=cfg.estimator_id,
            is_provisional=True,
            disclaimer=cfg.disclaimer,
            confidence_threshold_used=cfg.confidence_threshold,
            baseline_version_used=provisional.baseline_version_used,
        )

        return FatigueEstimationResult(
            timestamp=provisional.timestamp,
            fatigue_score=None,  # Option B: continuous score strictly None
            fatigue_state=final_state,
            confidence=confidence,
            dominant_factors=dominant_factors[:cfg.max_dominant_factors],
            overall_sqi=overall_sqi,
            metadata=metadata,
        )
