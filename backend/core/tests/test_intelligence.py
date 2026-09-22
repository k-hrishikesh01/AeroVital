"""Unit tests for Intelligence & State Estimation Layer in AeroVital Core.

Tests cover:
1. Contextual workload gating via G-load
2. Contextual workload gating via high-workload mission phase
3. Contextual workload gating via physical activity intensity
4. Autonomic fatigue pattern with confirmed benign cruise phase
5. Autonomic fatigue pattern with confirmed low G-load
6. CRITICAL: Missing G-load does NOT satisfy benign workload predicate
7. Positive normal confirmation requires both HR delta and RMSSD ratio
8. No-fatigue does not default to NORMAL (abstains on missing baseline)
9. Partial baseline prevents NORMAL confirmation
10. Motion corruption screening suppresses affected physiological features
11. Channel usability screening suppresses affected physiological features
12. Option B compliance: provisional_score is strictly None across all states
13. Contradictory evidence handling
14. Baseline version provenance preservation
15. Input immutability (FeatureVector, OperationalContext, QualityAssessment)
"""

from datetime import datetime, timezone
import pytest

from backend.core.schemas.context import MissionPhase, OperationalContext
from backend.core.schemas.features import (
    BaselineComparisonFeatures,
    FeatureVector,
    HeartRateFeatures,
    HRVFeatures,
    MotionFeatures,
)
from backend.core.schemas.quality import ChannelQuality, QualityAssessment
from backend.core.schemas.result import FatigueState
from backend.core.intelligence.config import EstimatorConfig
from backend.core.intelligence.estimator import ProvisionalRuleBasedEstimator


# =====================================================================
# Fixtures & Helpers
# =====================================================================

@pytest.fixture
def now() -> datetime:
    """Fixed reference timestamp."""
    return datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


def make_features(
    now: datetime,
    hr_dev: float | None = None,
    rmssd_ratio: float | None = None,
    activity: float | None = None,
    baseline_available: bool = True,
) -> FeatureVector:
    """Helper to build a FeatureVector for intelligence testing."""
    return FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=75.0),
        hrv_features=HRVFeatures(mean_rr_ms=800.0, rmssd_ms=45.0, valid_intervals_count=50),
        motion_features=MotionFeatures(mean_magnitude=1.0, activity_intensity=activity),
        baseline_features=BaselineComparisonFeatures(
            baseline_available=baseline_available,
            hr_deviation_from_baseline=hr_dev,
            hrv_rmssd_ratio_to_baseline=rmssd_ratio,
        ),
    )


def make_quality(
    now: datetime,
    hr_usable: bool = True,
    rr_usable: bool = True,
    motion_corruption: float = 0.0,
) -> QualityAssessment:
    """Helper to construct a QualityAssessment."""
    return QualityAssessment(
        timestamp=now,
        overall_sqi=0.95,
        motion_corruption_index=motion_corruption,
        is_telemetry_acceptable=True,
        channels={
            "heart_rate": ChannelQuality(channel_name="heart_rate", sqi_score=0.95, is_usable=hr_usable),
            "rr_interval": ChannelQuality(channel_name="rr_interval", sqi_score=0.95, is_usable=rr_usable),
        },
    )


# =====================================================================
# 1. Contextual Workload Gating
# =====================================================================

def test_contextual_workload_g_load(now):
    """Verify elevated HR with high G-load triggers ELEVATED_WORKLOAD, not FATIGUE."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=18.0, rmssd_ratio=0.90)
    context = OperationalContext(timestamp=now, external_g_load=3.5)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.ELEVATED_WORKLOAD
    assert any("High G-load" in f for f in res.dominant_factors)
    assert res.provisional_score is None


def test_contextual_workload_phase(now):
    """Verify elevated HR with combat maneuver phase triggers ELEVATED_WORKLOAD."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=15.0, rmssd_ratio=0.88)
    context = OperationalContext(timestamp=now, mission_phase=MissionPhase.COMBAT_MANEUVER)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.ELEVATED_WORKLOAD
    assert any("COMBAT_MANEUVER" in f for f in res.dominant_factors)


def test_contextual_workload_activity(now):
    """Verify elevated HR with high dynamic motion triggers ELEVATED_WORKLOAD."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=16.0, rmssd_ratio=0.90, activity=0.45)
    # No context provided, but somatic motion explains HR elevation
    res = estimator.evaluate(features, context=None)

    assert res.candidate_state == FatigueState.ELEVATED_WORKLOAD
    assert any("dynamic physical motion" in f.lower() for f in res.dominant_factors)


# =====================================================================
# 2. Autonomic Fatigue Pattern & Positive Benign Context
# =====================================================================

def test_autonomic_fatigue_pattern_cruise(now):
    """Verify depressed RMSSD ratio with confirmed benign cruise phase triggers FATIGUE."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=0.55)
    context = OperationalContext(timestamp=now, mission_phase=MissionPhase.CRUISE)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.FATIGUE
    assert any("Depressed beat-to-beat variability" in f for f in res.dominant_factors)
    assert any("CRUISE" in f for f in res.dominant_factors)


def test_autonomic_fatigue_pattern_low_g(now):
    """Verify depressed RMSSD ratio with confirmed low G-load triggers FATIGUE."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=0.50)
    context = OperationalContext(timestamp=now, external_g_load=1.0)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.FATIGUE
    assert any("Confirmed low G-load" in f for f in res.dominant_factors)


def test_critical_missing_g_load_does_not_satisfy_benign_workload(now):
    """CRITICAL: Missing G-load (None) must NOT satisfy benign context.
    
    When G-load is None and phase is None, benign context is unverified.
    Estimator must NOT assign FATIGUE merely because RMSSD ratio is low.
    """
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=0.50)
    # Context is None (or context with G-load=None and phase=None)
    context_missing = OperationalContext(timestamp=now, external_g_load=None, mission_phase=None)

    res = estimator.evaluate(features, context=context_missing)

    # Must NOT be FATIGUE!
    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert any("unverified by operational context" in f for f in res.dominant_factors)


# =====================================================================
# 3. Positive Normal Confirmation
# =====================================================================

def test_positive_normal_confirmation(now):
    """Verify NORMAL requires both HR delta and RMSSD ratio in nominal range + calm context."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.NORMAL
    assert any("Positive baseline concordance" in f for f in res.dominant_factors)


def test_no_fatigue_does_not_default_to_normal(now):
    """Verify that absence of fatigue does NOT default to NORMAL when baseline is missing."""
    estimator = ProvisionalRuleBasedEstimator()
    # Baseline unavailable: hr_dev and rmssd_ratio are None
    features = make_features(now, hr_dev=None, rmssd_ratio=None, baseline_available=False)
    context = OperationalContext(timestamp=now, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

    res = estimator.evaluate(features, context=context)

    # Must NOT default to NORMAL!
    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert any("baseline unavailable" in f.lower() for f in res.dominant_factors)


def test_partial_baseline_prevents_normal(now):
    """Verify that having HR baseline but missing RMSSD baseline prevents NORMAL confirmation."""
    estimator = ProvisionalRuleBasedEstimator()
    # HR delta is nominal, but RMSSD ratio is None
    features = make_features(now, hr_dev=1.5, rmssd_ratio=None, baseline_available=True)
    context = OperationalContext(timestamp=now, external_g_load=1.0)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert any("Incomplete physiological comparison" in f for f in res.dominant_factors)


# =====================================================================
# 4. Quality & Motion Screening
# =====================================================================

def test_motion_corruption_qualifies_channels(now):
    """Verify high motion corruption suppresses HR channel from triggering workload."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=20.0, rmssd_ratio=0.90)
    context = OperationalContext(timestamp=now, external_g_load=3.0)
    # Quality has severe motion corruption (> 0.60 threshold)
    quality_contaminated = make_quality(now, motion_corruption=0.85)

    res = estimator.evaluate(features, context=context, quality=quality_contaminated)

    # Since HR channel is motion-contaminated, workload cannot be confirmed
    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert any("unreliable or motion-corrupted" in f for f in res.dominant_factors)


def test_channel_unusable_screening(now):
    """Verify unusable RR channel suppresses RMSSD from triggering fatigue."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=0.0, rmssd_ratio=0.45)
    context = OperationalContext(timestamp=now, mission_phase=MissionPhase.CRUISE)
    # RR channel is unusable
    quality_bad_rr = make_quality(now, rr_usable=False)

    res = estimator.evaluate(features, context=context, quality=quality_bad_rr)

    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert any("unreliable or motion-corrupted" in f for f in res.dominant_factors)


# =====================================================================
# 5. Option B & Provenance & Immutability
# =====================================================================

def test_score_option_b_returns_none(now):
    """Verify Option B compliance: provisional_score is strictly None across all states."""
    estimator = ProvisionalRuleBasedEstimator()

    # Workload
    res_wl = estimator.evaluate(
        make_features(now, hr_dev=20.0, rmssd_ratio=0.9),
        context=OperationalContext(timestamp=now, external_g_load=3.0),
    )
    assert res_wl.provisional_score is None

    # Fatigue
    res_fat = estimator.evaluate(
        make_features(now, hr_dev=0.0, rmssd_ratio=0.4),
        context=OperationalContext(timestamp=now, mission_phase=MissionPhase.CRUISE),
    )
    assert res_fat.provisional_score is None

    # Normal
    res_norm = estimator.evaluate(
        make_features(now, hr_dev=1.0, rmssd_ratio=0.95),
        context=OperationalContext(timestamp=now, external_g_load=1.0),
    )
    assert res_norm.provisional_score is None

    # Insufficient
    res_insuf = estimator.evaluate(make_features(now, hr_dev=None, rmssd_ratio=None))
    assert res_insuf.provisional_score is None


def test_baseline_version_provenance(now):
    """Verify baseline version ID is faithfully carried into ProvisionalEstimationOutput."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)

    res = estimator.evaluate(
        features,
        context=context,
        baseline_version="2026-Q1-v2.5",
    )

    assert res.baseline_version_used == "2026-Q1-v2.5"


def test_input_immutability(now):
    """Verify FeatureVector, OperationalContext, and QualityAssessment are not mutated."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=15.0, rmssd_ratio=0.9)
    context = OperationalContext(timestamp=now, external_g_load=3.0)
    quality = make_quality(now)

    _ = estimator.evaluate(features, context=context, quality=quality)

    assert features.baseline_features.hr_deviation_from_baseline == 15.0
    assert context.external_g_load == 3.0
    assert quality.overall_sqi == 0.95


# =====================================================================
# 6. Hardening Tests for Strict Rule Boundaries & Contradiction Handling
# =====================================================================

def test_missing_baseline_hr_prevents_workload(now):
    """Verify missing baseline HR deviation prevents ELEVATED_WORKLOAD even with high G."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=None, rmssd_ratio=0.90)
    context = OperationalContext(timestamp=now, external_g_load=3.5)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["rule_workload"]["physio_supported"] is False
    assert res.rule_evidence_trace["rule_workload"]["physio_available"] is False
    assert any("Incomplete physiological comparison" in f for f in res.dominant_factors)


def test_missing_baseline_rmssd_prevents_fatigue(now):
    """Verify missing baseline RMSSD ratio prevents FATIGUE even during benign cruise."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=None)
    context = OperationalContext(timestamp=now, mission_phase=MissionPhase.CRUISE)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["rule_fatigue"]["autonomic_supported"] is False
    assert res.rule_evidence_trace["rule_fatigue"]["autonomic_available"] is False
    assert any("Incomplete physiological comparison" in f for f in res.dominant_factors)


def test_high_motion_corruption_cannot_create_workload(now):
    """Verify motion_corruption_index represents signal contamination, never workload."""
    estimator = ProvisionalRuleBasedEstimator()
    # High motion corruption, but nominal HR and no dynamic activity
    features = make_features(now, hr_dev=0.0, rmssd_ratio=0.90, activity=None)
    quality = make_quality(now, motion_corruption=0.85)

    res = estimator.evaluate(features, quality=quality)

    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    # Motion corruption must not appear in workload context reasons
    assert not any("High dynamic physical motion" in r for r in res.rule_evidence_trace["rule_workload"]["context_reasons"])
    assert res.rule_evidence_trace["rule_workload"]["rule_supported"] is False


def test_activity_alone_cannot_create_workload_without_physio_activation(now):
    """Verify high physical motion alone cannot create ELEVATED_WORKLOAD if HR is not elevated."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=0.90, activity=0.75)
    context = OperationalContext(timestamp=now, external_g_load=1.0)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state != FatigueState.ELEVATED_WORKLOAD
    assert res.rule_evidence_trace["rule_workload"]["physio_supported"] is False
    assert res.rule_evidence_trace["rule_workload"]["rule_supported"] is False


def test_low_rmssd_without_benign_context_cannot_create_fatigue(now):
    """Verify low RMSSD ratio without positive benign operational context abstains."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=0.0, rmssd_ratio=0.45)
    # Context is None completely
    res = estimator.evaluate(features, context=None)

    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["rule_fatigue"]["context_supported"] is False
    assert any("unverified by operational context" in f for f in res.dominant_factors)


def test_low_rmssd_plus_high_g_load_does_not_become_fatigue(now):
    """Verify low RMSSD under high G-load is contradicted and does not silently become FATIGUE."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=0.45)
    context = OperationalContext(timestamp=now, external_g_load=4.0)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state != FatigueState.FATIGUE
    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["rule_fatigue"]["contradictory_workload"] is True
    assert res.rule_evidence_trace["rule_fatigue"]["rule_supported"] is False
    assert any("contradicted by high operational workload" in f for f in res.dominant_factors)


def test_unknown_mission_phase_cannot_count_as_benign(now):
    """Verify MissionPhase.UNKNOWN cannot satisfy benign context for fatigue."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=0.0, rmssd_ratio=0.45)
    context = OperationalContext(timestamp=now, mission_phase=MissionPhase.UNKNOWN)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state != FatigueState.FATIGUE
    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["rule_fatigue"]["context_supported"] is False


def test_unknown_mission_phase_cannot_count_as_workload(now):
    """Verify MissionPhase.UNKNOWN cannot satisfy positive workload context."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=25.0, rmssd_ratio=0.90)
    context = OperationalContext(timestamp=now, mission_phase=MissionPhase.UNKNOWN)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state != FatigueState.ELEVATED_WORKLOAD
    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["rule_workload"]["context_supported"] is False
    assert any("unverified by operational workload context" in f for f in res.dominant_factors)


def test_no_absolute_hr_fallback(now):
    """Verify raw absolute heart rate is not used as fallback when baseline delta is missing."""
    estimator = ProvisionalRuleBasedEstimator()
    # High raw heart rate (160 BPM), but baseline delta is None
    features = FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=160.0),
        hrv_features=HRVFeatures(mean_rr_ms=375.0, rmssd_ms=45.0, valid_intervals_count=50),
        baseline_features=BaselineComparisonFeatures(
            baseline_available=False,
            hr_deviation_from_baseline=None,
            hrv_rmssd_ratio_to_baseline=None,
        ),
    )
    context = OperationalContext(timestamp=now, external_g_load=3.5)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state != FatigueState.ELEVATED_WORKLOAD
    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["rule_workload"]["physio_supported"] is False


def test_no_absolute_rmssd_fallback(now):
    """Verify raw absolute RMSSD is not used as fallback when baseline ratio is missing."""
    estimator = ProvisionalRuleBasedEstimator()
    # Extremely low raw RMSSD (10 ms), but baseline ratio is None
    features = FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=70.0),
        hrv_features=HRVFeatures(mean_rr_ms=850.0, rmssd_ms=10.0, valid_intervals_count=50),
        baseline_features=BaselineComparisonFeatures(
            baseline_available=False,
            hr_deviation_from_baseline=None,
            hrv_rmssd_ratio_to_baseline=None,
        ),
    )
    context = OperationalContext(timestamp=now, mission_phase=MissionPhase.CRUISE)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state != FatigueState.FATIGUE
    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["rule_fatigue"]["autonomic_supported"] is False


def test_flight_duration_cannot_independently_trigger_fatigue(now):
    """Verify high flight duration alone cannot independently trigger FATIGUE."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    # Long duration (10 hours = 36000s), but nominal metrics and cruise phase
    context = OperationalContext(
        timestamp=now,
        external_g_load=1.0,
        flight_duration_sec=36000.0,
        mission_phase=MissionPhase.CRUISE,
    )

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.NORMAL
    assert res.candidate_state != FatigueState.FATIGUE


def test_step7_does_not_gate_on_overall_sqi(now):
    """Verify Step 7 does not perform global overall_sqi thresholding (owned by Step 8)."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    # Overall SQI is low, is_telemetry_acceptable=False, but channels are marked usable
    quality_low_overall = QualityAssessment(
        timestamp=now,
        overall_sqi=0.15,
        is_telemetry_acceptable=False,
        motion_corruption_index=0.0,
        channels={
            "heart_rate": ChannelQuality(channel_name="heart_rate", sqi_score=0.90, is_usable=True),
            "rr_interval": ChannelQuality(channel_name="rr_interval", sqi_score=0.90, is_usable=True),
        },
    )

    res = estimator.evaluate(features, context=context, quality=quality_low_overall)

    # Step 7 evaluates evidence; Step 8 gates overall SQI
    assert res.candidate_state == FatigueState.NORMAL


def test_simultaneous_contradictory_evidence_handled_explicitly(now):
    """Verify simultaneous support for conflicting states resolves to INSUFFICIENT_DATA."""
    # Configure custom parameters that create an overlap between workload and normal
    custom_cfg = EstimatorConfig(
        hr_deviation_workload_threshold=10.0,
        hr_deviation_nominal_max=15.0,
        g_load_workload_threshold=0.8,
        g_load_nominal_max=1.2,
    )
    estimator = ProvisionalRuleBasedEstimator(config=custom_cfg)
    # hr_dev=12.0 satisfies both workload (> 10.0) and normal (<= 15.0)
    # external_g_load=1.0 satisfies workload (> 0.8) and normal (<= 1.2)
    features = make_features(now, hr_dev=12.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)

    res = estimator.evaluate(features, context=context)

    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    assert res.rule_evidence_trace["contradiction_detected"] is True
    assert "ELEVATED_WORKLOAD" in res.rule_evidence_trace["conflicting_states"]
    assert "NORMAL" in res.rule_evidence_trace["conflicting_states"]
    assert any("Contradictory state evidence" in f for f in res.dominant_factors)


def test_rule_trace_records_unsupported_predicates(now):
    """Verify rule_evidence_trace comprehensively records unsupported predicates and availability."""
    estimator = ProvisionalRuleBasedEstimator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=0.50)
    # No context provided
    res = estimator.evaluate(features, context=None)

    assert res.candidate_state == FatigueState.INSUFFICIENT_DATA
    trace = res.rule_evidence_trace

    # Workload trace
    assert trace["rule_workload"]["physio_supported"] is False
    assert trace["rule_workload"]["context_supported"] is False
    assert trace["rule_workload"]["rule_supported"] is False

    # Fatigue trace
    assert trace["rule_fatigue"]["autonomic_supported"] is True
    assert trace["rule_fatigue"]["context_supported"] is False
    assert trace["rule_fatigue"]["rule_supported"] is False

    # Normal trace
    assert trace["rule_normal"]["hr_concordance_supported"] is True
    assert trace["rule_normal"]["rmssd_concordance_supported"] is False
    assert trace["rule_normal"]["physio_concordance_supported"] is False
    assert trace["rule_normal"]["rule_supported"] is False

    # Contradiction flag
    assert trace["contradiction_detected"] is False
