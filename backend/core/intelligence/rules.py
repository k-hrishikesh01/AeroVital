"""Structural Rule Engine for AeroVital State Estimation.

Evaluates evidence sufficiency, contextual workload differentiation, autonomic fatigue,
and positive normal confirmation.

STRICT PRINCIPLES:
1. Each rule explicitly declares required operands; missing evidence never satisfies a predicate.
2. G-load = None is UNAVAILABLE; it never defaults to 1.0g or satisfies benign context.
3. FATIGUE requires autonomic degradation PLUS positively established benign context.
4. ELEVATED_WORKLOAD requires physiological activation PLUS positive workload context.
5. NORMAL requires positive baseline concordance for both HR and RMSSD; lack of fatigue does not imply normal.
6. Option B: provisional_score is strictly None.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.core.schemas.context import MissionPhase, OperationalContext
from backend.core.schemas.features import FeatureVector
from backend.core.schemas.quality import QualityAssessment
from backend.core.schemas.result import FatigueState
from backend.core.intelligence.config import EstimatorConfig


class ProvisionalEstimationOutput(BaseModel):
    """Intermediate evaluation emitted by Step 7 for Step 8 consumption."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(..., description="Observation timestamp.")
    candidate_state: FatigueState = Field(..., description="Candidate operational state.")
    provisional_score: Optional[float] = Field(default=None, description="Continuous score (strictly None under Option B).")
    dominant_factors: List[str] = Field(default_factory=list, description="Top explanatory rationale strings.")
    rule_evidence_trace: Dict[str, Any] = Field(default_factory=dict, description="Audit trail of evaluated predicates.")
    baseline_version_used: Optional[str] = Field(default=None, description="Pilot baseline version ID if available.")


def is_channel_reliable(
    quality: Optional[QualityAssessment],
    channel_name: str,
    config: EstimatorConfig,
) -> bool:
    """Check whether a specific physiological channel is usable and uncontaminated by motion."""
    if quality is None:
        return True

    ch = quality.channels.get(channel_name)
    if ch is not None and not ch.is_usable:
        return False

    if quality.motion_corruption_index > config.motion_corruption_threshold:
        return False

    return True


def evaluate_state_rules(
    features: FeatureVector,
    context: Optional[OperationalContext] = None,
    quality: Optional[QualityAssessment] = None,
    config: Optional[EstimatorConfig] = None,
    baseline_version: Optional[str] = None,
) -> ProvisionalEstimationOutput:
    """Evaluate structural evidence rules to determine the candidate operational state.
    
    Args:
        features: FeatureVector with descriptive and baseline comparison metrics.
        context: Optional flight context (G-load, phase, duration). Never defaulted.
        quality: Optional quality assessment for channel screening.
        config: Centralized prototype engineering parameters.
        baseline_version: Provenance version ID of the pilot baseline, if available.
        
    Returns:
        ProvisionalEstimationOutput containing candidate state and audit trace.
    """
    cfg = config or EstimatorConfig()
    ts = features.window_end

    trace: Dict[str, Any] = {}
    dominant_factors: List[str] = []

    # Channel reliability checks
    hr_reliable = is_channel_reliable(quality, "heart_rate", cfg)
    rr_reliable = is_channel_reliable(quality, "rr_interval", cfg)
    trace["hr_channel_reliable"] = hr_reliable
    trace["rr_channel_reliable"] = rr_reliable

    # Baseline comparison metrics
    hr_dev = features.baseline_features.hr_deviation_from_baseline
    rmssd_ratio = features.baseline_features.hrv_rmssd_ratio_to_baseline
    baseline_available = features.baseline_features.baseline_available
    trace["baseline_available"] = baseline_available
    trace["hr_deviation"] = hr_dev
    trace["rmssd_ratio"] = rmssd_ratio

    # Context & motion metrics (strictly un-defaulted; no-imputation contract)
    external_g_load = context.external_g_load if context is not None else None
    mission_phase = context.mission_phase if context is not None else None
    activity_intensity = features.motion_features.activity_intensity
    trace["external_g_load"] = external_g_load
    trace["mission_phase"] = mission_phase.value if mission_phase is not None else None
    trace["activity_intensity"] = activity_intensity

    # -------------------------------------------------------------------------
    # RULE 1: ELEVATED_WORKLOAD
    # Requires physiological activation PLUS positive workload context.
    # No absolute-HR fallback; missing context never satisfies predicate.
    # -------------------------------------------------------------------------
    hr_dev_available = (hr_dev is not None and hr_reliable)
    workload_physio = (
        hr_dev_available
        and hr_dev > cfg.hr_deviation_workload_threshold
    )

    workload_context_reasons: List[str] = []
    if external_g_load is not None and external_g_load > cfg.g_load_workload_threshold:
        workload_context_reasons.append(f"High G-load ({external_g_load:.1f}g)")
    if mission_phase is not None and mission_phase in cfg.high_workload_phases:
        workload_context_reasons.append(f"High-workload flight phase ({mission_phase.value})")
    if activity_intensity is not None and activity_intensity > cfg.activity_workload_threshold:
        workload_context_reasons.append(f"High dynamic physical motion ({activity_intensity:.2f})")

    workload_context = len(workload_context_reasons) > 0
    workload_supported = workload_physio and workload_context

    trace["rule_workload"] = {
        "physio_available": hr_dev_available,
        "physio_supported": workload_physio,
        "context_available": (external_g_load is not None or mission_phase is not None or activity_intensity is not None),
        "context_supported": workload_context,
        "context_reasons": workload_context_reasons,
        "rule_supported": workload_supported,
    }

    # -------------------------------------------------------------------------
    # RULE 2: FATIGUE
    # Requires autonomic degradation PLUS positively established benign context.
    # Missing G-load is unavailable, NOT nominal; missing phase is unavailable, NOT benign.
    # No absolute-RMSSD fallback; flight duration is not a fatigue trigger.
    # -------------------------------------------------------------------------
    rmssd_ratio_available = (rmssd_ratio is not None and rr_reliable)
    fatigue_autonomic = (
        rmssd_ratio_available
        and rmssd_ratio < cfg.rmssd_ratio_fatigue_threshold
    )

    benign_context_reasons: List[str] = []
    if external_g_load is not None and external_g_load <= cfg.g_load_nominal_max:
        benign_context_reasons.append(f"Confirmed low G-load ({external_g_load:.1f}g)")
    if mission_phase is not None and mission_phase in cfg.benign_phases:
        benign_context_reasons.append(f"Confirmed benign flight phase ({mission_phase.value})")

    g_load_contradictory = (external_g_load is not None and external_g_load > cfg.g_load_workload_threshold)
    phase_contradictory = (mission_phase is not None and mission_phase in cfg.high_workload_phases)
    activity_contradictory = (activity_intensity is not None and activity_intensity > cfg.activity_workload_threshold)
    contradictory_workload = (g_load_contradictory or phase_contradictory or activity_contradictory)

    fatigue_context = len(benign_context_reasons) > 0 and not contradictory_workload
    fatigue_supported = fatigue_autonomic and fatigue_context

    trace["rule_fatigue"] = {
        "autonomic_available": rmssd_ratio_available,
        "autonomic_supported": fatigue_autonomic,
        "benign_context_available": (external_g_load is not None or mission_phase is not None),
        "context_supported": fatigue_context,
        "benign_reasons": benign_context_reasons,
        "contradictory_workload": contradictory_workload,
        "rule_supported": fatigue_supported,
    }

    # -------------------------------------------------------------------------
    # RULE 3: NORMAL
    # Requires positive baseline concordance on BOTH HR and RMSSD.
    # Missing either required comparison prevents NORMAL.
    # Context must be free of acute operational strain.
    # -------------------------------------------------------------------------
    normal_hr_concordant = (
        hr_dev_available
        and abs(hr_dev) <= cfg.hr_deviation_nominal_max
    )
    normal_rmssd_concordant = (
        rmssd_ratio_available
        and rmssd_ratio >= cfg.rmssd_ratio_nominal_min
    )
    normal_physio = normal_hr_concordant and normal_rmssd_concordant

    acute_strain = (
        (external_g_load is not None and external_g_load > cfg.g_load_nominal_max)
        or (mission_phase is not None and mission_phase in cfg.high_workload_phases)
        or (activity_intensity is not None and activity_intensity > cfg.activity_workload_threshold)
    )
    normal_context = not acute_strain
    normal_supported = normal_physio and normal_context

    trace["rule_normal"] = {
        "hr_concordance_available": hr_dev_available,
        "hr_concordance_supported": normal_hr_concordant,
        "rmssd_concordance_available": rmssd_ratio_available,
        "rmssd_concordance_supported": normal_rmssd_concordant,
        "physio_concordance_supported": normal_physio,
        "context_supported": normal_context,
        "acute_strain": acute_strain,
        "rule_supported": normal_supported,
    }

    # -------------------------------------------------------------------------
    # STATE RESOLUTION & CONTRADICTION HANDLING
    # Inspect all supported states; rule ordering must never pick a silent winner.
    # -------------------------------------------------------------------------
    supported_states: List[FatigueState] = []
    if workload_supported:
        supported_states.append(FatigueState.ELEVATED_WORKLOAD)
    if fatigue_supported:
        supported_states.append(FatigueState.FATIGUE)
    if normal_supported:
        supported_states.append(FatigueState.NORMAL)

    if len(supported_states) > 1:
        trace["contradiction_detected"] = True
        trace["conflicting_states"] = [s.value for s in supported_states]
        dominant_factors = [
            f"Contradictory state evidence: simultaneously supports {', '.join(s.value for s in supported_states)}"
        ]
        return ProvisionalEstimationOutput(
            timestamp=ts,
            candidate_state=FatigueState.INSUFFICIENT_DATA,
            provisional_score=None,
            dominant_factors=dominant_factors,
            rule_evidence_trace=trace,
            baseline_version_used=baseline_version,
        )

    trace["contradiction_detected"] = False

    if len(supported_states) == 1:
        resolved_state = supported_states[0]
        if resolved_state == FatigueState.ELEVATED_WORKLOAD:
            dominant_factors.append(f"Elevated heart rate (+{hr_dev:.1f} BPM relative to baseline)")
            dominant_factors.extend(workload_context_reasons)
        elif resolved_state == FatigueState.FATIGUE:
            dominant_factors.append(f"Depressed beat-to-beat variability (RMSSD ratio: {rmssd_ratio:.2f})")
            dominant_factors.extend(benign_context_reasons)
        elif resolved_state == FatigueState.NORMAL:
            dominant_factors.append("Positive baseline concordance: HR and RMSSD within nominal limits")

        return ProvisionalEstimationOutput(
            timestamp=ts,
            candidate_state=resolved_state,
            provisional_score=None,
            dominant_factors=dominant_factors[:3],
            rule_evidence_trace=trace,
            baseline_version_used=baseline_version,
        )

    # -------------------------------------------------------------------------
    # RULE 4: INSUFFICIENT_DATA (Evidence Insufficiency)
    # No state was supported. Provide specific explanatory rationale.
    # -------------------------------------------------------------------------
    if not baseline_available:
        dominant_factors.append("Calibrated pilot baseline unavailable")
    elif not hr_reliable or not rr_reliable:
        dominant_factors.append("Physiological sensor channels unreliable or motion-corrupted")
    elif hr_dev is None or rmssd_ratio is None:
        dominant_factors.append("Incomplete physiological comparison metrics in window")
    elif fatigue_autonomic and not fatigue_context:
        if contradictory_workload:
            dominant_factors.append("Autonomic suppression observed but contradicted by high operational workload")
        else:
            dominant_factors.append("Autonomic suppression observed but unverified by operational context")
    elif workload_physio and not workload_context:
        dominant_factors.append("Physiological activation observed but unverified by operational workload context")
    elif normal_physio and not normal_context:
        dominant_factors.append("Baseline concordance observed but invalidated by acute operational strain")
    else:
        dominant_factors.append("Evidence insufficient or unconfirmed for any operational state")

    return ProvisionalEstimationOutput(
        timestamp=ts,
        candidate_state=FatigueState.INSUFFICIENT_DATA,
        provisional_score=None,
        dominant_factors=dominant_factors[:3],
        rule_evidence_trace=trace,
        baseline_version_used=baseline_version,
    )
