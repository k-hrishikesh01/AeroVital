"""Unit tests for Confidence Evaluation & Final Result Generation Layer (Step 8).

Tests cover:
1. Confidence bounded in [0.0, 1.0] across edge cases
2. High-quality supported candidate retains candidate state (NORMAL, ELEVATED_WORKLOAD, FATIGUE)
3. Low global SQI forces INSUFFICIENT_DATA
4. Globally unacceptable telemetry forces INSUFFICIENT_DATA
5. Step 7 INSUFFICIENT_DATA strictly remains INSUFFICIENT_DATA
6. Insufficient evidence confidence causes abstention
7. Adequate evidence confidence preserves candidate
8. Missing required evidence cannot increase confidence
9. No fabrication/imputation of missing channels or features
10. Baseline version provenance preservation
11. Explanation and dominant factors preservation
12. Input immutability
13. Confidence calculation determinism
14. No Step 7 state rules are duplicated in Step 8
15. Option B compliance: fatigue_score strictly remains None
16. Monotonicity across all dimensions (evidence removal, channel degradation, SQI degradation, motion corruption)
17. State non-transformation (Step 8 cannot morph a supported state into another supported state)
18. Optional channels (SpO2, skin temperature, accelerometer) do not cause arbitrary penalties
19. Edge cases: exact thresholds, just below thresholds, exactly 0.0, exactly 1.0
20. Contradicted evidence trace zeros completeness
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
from backend.core.intelligence.estimator import ProvisionalRuleBasedEstimator
from backend.core.intelligence.rules import ProvisionalEstimationOutput
from backend.core.confidence.config import ConfidenceConfig
from backend.core.confidence.evaluator import (
    ConfidenceBreakdown,
    ConfidenceEvaluator,
    compute_evidence_completeness_score,
)


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
    """Helper to build a FeatureVector."""
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
    overall_sqi: float = 0.95,
    is_telemetry_acceptable: bool = True,
    hr_usable: bool = True,
    hr_sqi: float = 0.95,
    rr_usable: bool = True,
    rr_sqi: float = 0.95,
    accel_usable: bool = True,
    accel_sqi: float = 0.90,
    motion_corruption: float = 0.0,
    include_optional: bool = False,
) -> QualityAssessment:
    """Helper to construct a QualityAssessment."""
    channels = {
        "heart_rate": ChannelQuality(channel_name="heart_rate", sqi_score=hr_sqi, is_usable=hr_usable),
        "rr_interval": ChannelQuality(channel_name="rr_interval", sqi_score=rr_sqi, is_usable=rr_usable),
        "accelerometer": ChannelQuality(channel_name="accelerometer", sqi_score=accel_sqi, is_usable=accel_usable),
    }
    if include_optional:
        channels["spo2"] = ChannelQuality(channel_name="spo2", sqi_score=0.98, is_usable=True)
        channels["skin_temperature"] = ChannelQuality(channel_name="skin_temperature", sqi_score=0.97, is_usable=True)

    return QualityAssessment(
        timestamp=now,
        overall_sqi=overall_sqi,
        motion_corruption_index=motion_corruption,
        is_telemetry_acceptable=is_telemetry_acceptable,
        channels=channels,
    )


def get_step7_provisional(
    features: FeatureVector,
    context: OperationalContext | None = None,
    quality: QualityAssessment | None = None,
    baseline_version: str | None = "2026-v1.0",
) -> ProvisionalEstimationOutput:
    """Run Step 7 estimator to generate authentic ProvisionalEstimationOutput."""
    estimator = ProvisionalRuleBasedEstimator()
    return estimator.evaluate(
        features=features,
        context=context,
        quality=quality,
        baseline_version=baseline_version,
    )


# =====================================================================
# 1. Bounded Confidence & Determinism
# =====================================================================

def test_confidence_bounded_zero_to_one(now):
    """Verify confidence is strictly bounded in [0.0, 1.0] across extreme conditions."""
    evaluator = ConfidenceEvaluator()

    # Extreme poor quality
    features_poor = make_features(now, hr_dev=None, rmssd_ratio=None, baseline_available=False)
    quality_poor = make_quality(
        now,
        overall_sqi=0.0,
        is_telemetry_acceptable=False,
        hr_usable=False,
        hr_sqi=0.0,
        rr_usable=False,
        rr_sqi=0.0,
        motion_corruption=1.0,
    )
    prov_poor = get_step7_provisional(features_poor, quality=quality_poor)
    res_poor = evaluator.evaluate(prov_poor, quality=quality_poor, features=features_poor)

    assert 0.0 <= res_poor.confidence <= 1.0
    assert res_poor.confidence == 0.0

    # Extreme pristine quality
    features_good = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    quality_good = make_quality(now, overall_sqi=1.0, hr_sqi=1.0, rr_sqi=1.0, motion_corruption=0.0)
    context_good = OperationalContext(timestamp=now, external_g_load=1.0)
    prov_good = get_step7_provisional(features_good, context=context_good, quality=quality_good)
    res_good = evaluator.evaluate(prov_good, quality=quality_good, features=features_good, context=context_good)

    assert 0.0 <= res_good.confidence <= 1.0
    assert res_good.confidence == 1.0


def test_confidence_calculation_is_deterministic(now):
    """Verify repeated evaluations on identical data produce identical confidence scores."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=2.0, rmssd_ratio=0.92)
    quality = make_quality(now, overall_sqi=0.88)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context, quality=quality)

    confidences = [
        evaluator.evaluate(prov, quality=quality, features=features, context=context).confidence
        for _ in range(10)
    ]

    assert len(set(confidences)) == 1


# =====================================================================
# 2. Supported Candidate Handling (NORMAL, ELEVATED_WORKLOAD, FATIGUE)
# =====================================================================

def test_high_quality_supported_candidate_retains_normal(now):
    """Verify high-quality supported NORMAL candidate is retained."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.5, rmssd_ratio=0.95)
    quality = make_quality(now, overall_sqi=0.92)
    context = OperationalContext(timestamp=now, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
    prov = get_step7_provisional(features, context=context, quality=quality)

    assert prov.candidate_state == FatigueState.NORMAL
    res = evaluator.evaluate(prov, quality=quality, features=features, context=context)

    assert res.fatigue_state == FatigueState.NORMAL
    assert res.confidence >= 0.40
    assert any("Positive baseline concordance" in f for f in res.dominant_factors)


def test_high_quality_supported_candidate_retains_workload(now):
    """Verify high-quality supported ELEVATED_WORKLOAD candidate is retained."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=20.0, rmssd_ratio=0.88)
    quality = make_quality(now, overall_sqi=0.90)
    context = OperationalContext(timestamp=now, external_g_load=3.5)
    prov = get_step7_provisional(features, context=context, quality=quality)

    assert prov.candidate_state == FatigueState.ELEVATED_WORKLOAD
    res = evaluator.evaluate(prov, quality=quality, features=features, context=context)

    assert res.fatigue_state == FatigueState.ELEVATED_WORKLOAD
    assert res.confidence >= 0.40
    assert any("High G-load" in f for f in res.dominant_factors)


def test_high_quality_supported_candidate_retains_fatigue(now):
    """Verify high-quality supported FATIGUE candidate is retained."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.55)
    quality = make_quality(now, overall_sqi=0.90)
    context = OperationalContext(timestamp=now, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
    prov = get_step7_provisional(features, context=context, quality=quality)

    assert prov.candidate_state == FatigueState.FATIGUE
    res = evaluator.evaluate(prov, quality=quality, features=features, context=context)

    assert res.fatigue_state == FatigueState.FATIGUE
    assert res.confidence >= 0.40
    assert any("Depressed beat-to-beat variability" in f for f in res.dominant_factors)


# =====================================================================
# 3. Global SQI & Acceptability Gates
# =====================================================================

def test_low_global_sqi_forces_insufficient_data(now):
    """Verify low global SQI forces INSUFFICIENT_DATA even if Step 7 found FATIGUE."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.55)
    context = OperationalContext(timestamp=now, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
    prov = get_step7_provisional(features, context=context)
    assert prov.candidate_state == FatigueState.FATIGUE

    quality_low = make_quality(now, overall_sqi=0.30, is_telemetry_acceptable=True)

    res = evaluator.evaluate(prov, quality=quality_low, features=features, context=context)

    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA
    assert any("globally unacceptable" in f.lower() for f in res.dominant_factors)


def test_globally_unacceptable_telemetry_forces_insufficient_data(now):
    """Verify is_telemetry_acceptable=False forces INSUFFICIENT_DATA."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=20.0, rmssd_ratio=0.90)
    context = OperationalContext(timestamp=now, external_g_load=3.0)
    prov = get_step7_provisional(features, context=context)
    assert prov.candidate_state == FatigueState.ELEVATED_WORKLOAD

    quality_unacceptable = make_quality(now, overall_sqi=0.50, is_telemetry_acceptable=False)

    res = evaluator.evaluate(prov, quality=quality_unacceptable, features=features, context=context)

    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA
    assert any("globally unacceptable" in f.lower() for f in res.dominant_factors)


# =====================================================================
# 4. Confidence Abstention Gate
# =====================================================================

def test_step7_insufficient_data_remains_insufficient_data(now):
    """Verify Step 7 INSUFFICIENT_DATA strictly remains INSUFFICIENT_DATA even with high SQI."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=None, rmssd_ratio=None, baseline_available=False)
    prov = get_step7_provisional(features)
    assert prov.candidate_state == FatigueState.INSUFFICIENT_DATA

    quality_pristine = make_quality(now, overall_sqi=0.98)

    res = evaluator.evaluate(prov, quality=quality_pristine, features=features)

    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA
    assert any("baseline unavailable" in f.lower() for f in res.dominant_factors)


def test_insufficient_evidence_confidence_causes_abstention(now):
    """Verify confidence below threshold causes abstention to INSUFFICIENT_DATA."""
    custom_cfg = ConfidenceConfig(confidence_threshold=0.75)
    evaluator = ConfidenceEvaluator(config=custom_cfg)

    features = make_features(now, hr_dev=1.5, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    quality_marginal = make_quality(now, overall_sqi=0.50, hr_sqi=0.50, rr_sqi=0.50)
    prov = get_step7_provisional(features, context=context, quality=quality_marginal)

    res = evaluator.evaluate(prov, quality=quality_marginal, features=features, context=context)

    assert res.confidence < 0.75
    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA
    assert any("confidence inadequate" in f.lower() for f in res.dominant_factors)


# =====================================================================
# 5. Monotonicity Tests (Audit Point 6)
# =====================================================================

def test_monotonicity_removing_evidence_cannot_increase_confidence(now):
    """Verify removing required evidence strictly lowers or preserves confidence."""
    evaluator = ConfidenceEvaluator()
    quality = make_quality(now, overall_sqi=0.85)
    context = OperationalContext(timestamp=now, external_g_load=1.0)

    # Full evidence for NORMAL
    features_full = make_features(now, hr_dev=1.0, rmssd_ratio=0.95, baseline_available=True)
    prov_full = get_step7_provisional(features_full, context=context, quality=quality)
    c_full = evaluator.evaluate(prov_full, quality=quality, features=features_full, context=context).confidence

    # Partial evidence (missing RMSSD comparison)
    features_partial = make_features(now, hr_dev=1.0, rmssd_ratio=None, baseline_available=True)
    prov_partial = get_step7_provisional(features_partial, context=context, quality=quality)
    c_partial = evaluator.evaluate(prov_partial, quality=quality, features=features_partial, context=context).confidence

    assert c_partial < c_full


def test_monotonicity_degrading_relied_channel_cannot_increase_confidence(now):
    """Verify degrading relied-upon channel SQI strictly lowers confidence."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context)

    q_high = make_quality(now, overall_sqi=0.90, hr_sqi=0.95, rr_sqi=0.95)
    q_low = make_quality(now, overall_sqi=0.90, hr_sqi=0.45, rr_sqi=0.45)

    c_high = evaluator.evaluate(prov, quality=q_high, features=features, context=context).confidence
    c_low = evaluator.evaluate(prov, quality=q_low, features=features, context=context).confidence

    assert c_low < c_high


def test_monotonicity_degrading_global_sqi_cannot_increase_confidence(now):
    """Verify degrading overall SQI strictly lowers confidence."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context)

    q_high = make_quality(now, overall_sqi=0.95)
    q_low = make_quality(now, overall_sqi=0.55)

    c_high = evaluator.evaluate(prov, quality=q_high, features=features, context=context).confidence
    c_low = evaluator.evaluate(prov, quality=q_low, features=features, context=context).confidence

    assert c_low < c_high


def test_monotonicity_increasing_motion_corruption_cannot_increase_confidence(now):
    """Verify increasing motion corruption strictly lowers confidence."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context)

    q_calm = make_quality(now, overall_sqi=0.90, motion_corruption=0.0)
    q_shaky = make_quality(now, overall_sqi=0.90, motion_corruption=0.50)

    c_calm = evaluator.evaluate(prov, quality=q_calm, features=features, context=context).confidence
    c_shaky = evaluator.evaluate(prov, quality=q_shaky, features=features, context=context).confidence

    assert c_shaky < c_calm


# =====================================================================
# 6. Candidate Preservation & Non-Transformation (Audit Point 7 & 8)
# =====================================================================

def test_cannot_transform_supported_candidate_into_another_supported_state(now):
    """Verify Step 8 can only preserve the candidate or abstain to INSUFFICIENT_DATA."""
    evaluator = ConfidenceEvaluator()

    # NORMAL candidate
    features_n = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    prov_n = get_step7_provisional(features_n, context=OperationalContext(timestamp=now, external_g_load=1.0))
    for sqi in [0.95, 0.50, 0.20]:
        q = make_quality(now, overall_sqi=sqi, is_telemetry_acceptable=(sqi >= 0.40))
        res = evaluator.evaluate(prov_n, quality=q)
        assert res.fatigue_state in (FatigueState.NORMAL, FatigueState.INSUFFICIENT_DATA)
        assert res.fatigue_state not in (FatigueState.FATIGUE, FatigueState.ELEVATED_WORKLOAD)

    # WORKLOAD candidate
    features_w = make_features(now, hr_dev=20.0, rmssd_ratio=0.90)
    prov_w = get_step7_provisional(features_w, context=OperationalContext(timestamp=now, external_g_load=3.5))
    for sqi in [0.95, 0.50, 0.20]:
        q = make_quality(now, overall_sqi=sqi, is_telemetry_acceptable=(sqi >= 0.40))
        res = evaluator.evaluate(prov_w, quality=q)
        assert res.fatigue_state in (FatigueState.ELEVATED_WORKLOAD, FatigueState.INSUFFICIENT_DATA)
        assert res.fatigue_state not in (FatigueState.FATIGUE, FatigueState.NORMAL)

    # FATIGUE candidate
    features_f = make_features(now, hr_dev=1.0, rmssd_ratio=0.50)
    prov_f = get_step7_provisional(features_f, context=OperationalContext(timestamp=now, external_g_load=1.0, mission_phase=MissionPhase.CRUISE))
    for sqi in [0.95, 0.50, 0.20]:
        q = make_quality(now, overall_sqi=sqi, is_telemetry_acceptable=(sqi >= 0.40))
        res = evaluator.evaluate(prov_f, quality=q)
        assert res.fatigue_state in (FatigueState.FATIGUE, FatigueState.INSUFFICIENT_DATA)
        assert res.fatigue_state not in (FatigueState.NORMAL, FatigueState.ELEVATED_WORKLOAD)


def test_step7_insufficient_data_cannot_be_upgraded_adversarial(now):
    """Verify Step 7 INSUFFICIENT_DATA cannot be upgraded by perfect quality or features."""
    evaluator = ConfidenceEvaluator()
    # Uncalibrated baseline
    features = make_features(now, hr_dev=None, rmssd_ratio=None, baseline_available=False)
    prov = get_step7_provisional(features)
    assert prov.candidate_state == FatigueState.INSUFFICIENT_DATA

    # Maximum possible quality
    quality_perfect = make_quality(
        now,
        overall_sqi=1.0,
        is_telemetry_acceptable=True,
        hr_usable=True,
        hr_sqi=1.0,
        rr_usable=True,
        rr_sqi=1.0,
        accel_usable=True,
        accel_sqi=1.0,
        motion_corruption=0.0,
    )

    res = evaluator.evaluate(prov, quality=quality_perfect, features=features)

    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA


# =====================================================================
# 7. Optional Channels & Irrelevant Channel Penalty (Audit Point 3 & 13)
# =====================================================================

def test_missing_optional_channels_does_not_penalize_confidence(now):
    """Verify missing SpO2 and skin temperature do not reduce confidence for any candidate."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context)

    q_without = make_quality(now, overall_sqi=0.90, include_optional=False)
    q_with = make_quality(now, overall_sqi=0.90, include_optional=True)

    c_without = evaluator.evaluate(prov, quality=q_without).confidence
    c_with = evaluator.evaluate(prov, quality=q_with).confidence

    # Exactly identical because SpO2 and skin temperature are not relied-upon
    assert c_without == c_with


def test_missing_accel_does_not_penalize_fatigue_or_normal(now):
    """Verify missing accelerometer does not penalize FATIGUE or NORMAL states."""
    evaluator = ConfidenceEvaluator()

    # Quality with no accelerometer channel
    q_no_accel = QualityAssessment(
        timestamp=now,
        overall_sqi=0.90,
        is_telemetry_acceptable=True,
        channels={
            "heart_rate": ChannelQuality(channel_name="heart_rate", sqi_score=0.90, is_usable=True),
            "rr_interval": ChannelQuality(channel_name="rr_interval", sqi_score=0.90, is_usable=True),
        },
    )
    # Quality with accelerometer channel
    q_with_accel = QualityAssessment(
        timestamp=now,
        overall_sqi=0.90,
        is_telemetry_acceptable=True,
        channels={
            "heart_rate": ChannelQuality(channel_name="heart_rate", sqi_score=0.90, is_usable=True),
            "rr_interval": ChannelQuality(channel_name="rr_interval", sqi_score=0.90, is_usable=True),
            "accelerometer": ChannelQuality(channel_name="accelerometer", sqi_score=0.90, is_usable=True),
        },
    )

    # FATIGUE
    prov_f = get_step7_provisional(
        make_features(now, hr_dev=1.0, rmssd_ratio=0.50),
        context=OperationalContext(timestamp=now, external_g_load=1.0, mission_phase=MissionPhase.CRUISE),
    )
    c_f_no_accel = evaluator.evaluate(prov_f, quality=q_no_accel).confidence
    c_f_with_accel = evaluator.evaluate(prov_f, quality=q_with_accel).confidence
    assert c_f_no_accel == c_f_with_accel

    # NORMAL
    prov_n = get_step7_provisional(
        make_features(now, hr_dev=1.0, rmssd_ratio=0.95),
        context=OperationalContext(timestamp=now, external_g_load=1.0),
    )
    c_n_no_accel = evaluator.evaluate(prov_n, quality=q_no_accel).confidence
    c_n_with_accel = evaluator.evaluate(prov_n, quality=q_with_accel).confidence
    assert c_n_no_accel == c_n_with_accel


def test_missing_rr_does_not_penalize_workload(now):
    """Verify missing RR channel does not penalize ELEVATED_WORKLOAD."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=20.0, rmssd_ratio=None)
    context = OperationalContext(timestamp=now, external_g_load=3.5)
    prov = get_step7_provisional(features, context=context)
    assert prov.candidate_state == FatigueState.ELEVATED_WORKLOAD

    # Quality with unusable RR channel vs usable RR channel
    q_bad_rr = make_quality(now, overall_sqi=0.90, hr_sqi=0.90, rr_usable=False, rr_sqi=0.0)
    q_good_rr = make_quality(now, overall_sqi=0.90, hr_sqi=0.90, rr_usable=True, rr_sqi=0.90)

    c_bad_rr = evaluator.evaluate(prov, quality=q_bad_rr).confidence
    c_good_rr = evaluator.evaluate(prov, quality=q_good_rr).confidence

    # ELEVATED_WORKLOAD relies only on heart_rate; RR quality does not affect channel score
    assert c_bad_rr == c_good_rr


def test_missing_hr_does_not_penalize_fatigue(now):
    """Verify missing HR channel does not penalize FATIGUE."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=None, rmssd_ratio=0.50)
    context = OperationalContext(timestamp=now, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
    prov = get_step7_provisional(features, context=context)
    assert prov.candidate_state == FatigueState.FATIGUE

    # Quality with unusable HR channel vs usable HR channel
    q_bad_hr = make_quality(now, overall_sqi=0.90, hr_usable=False, hr_sqi=0.0, rr_sqi=0.90)
    q_good_hr = make_quality(now, overall_sqi=0.90, hr_usable=True, hr_sqi=0.90, rr_sqi=0.90)

    c_bad_hr = evaluator.evaluate(prov, quality=q_bad_hr).confidence
    c_good_hr = evaluator.evaluate(prov, quality=q_good_hr).confidence

    # FATIGUE relies only on rr_interval; HR quality does not affect channel score
    assert c_bad_hr == c_good_hr


# =====================================================================
# 8. Boundary & Edge Case Tests (Audit Point 14)
# =====================================================================

def test_boundary_overall_sqi_exactly_at_threshold(now):
    """Verify overall SQI exactly at 0.40 passes the global gate."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context)

    # overall_sqi exactly 0.40
    q_exact = make_quality(now, overall_sqi=0.40, hr_sqi=0.90, rr_sqi=0.90)
    res = evaluator.evaluate(prov, quality=q_exact)

    # Does not fail global SQI gate
    assert not any("globally unacceptable" in f.lower() for f in res.dominant_factors)


def test_boundary_overall_sqi_just_below_threshold(now):
    """Verify overall SQI just below 0.40 (0.399) fails the global gate."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context)

    q_just_below = make_quality(now, overall_sqi=0.399, hr_sqi=0.90, rr_sqi=0.90)
    res = evaluator.evaluate(prov, quality=q_just_below)

    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA
    assert any("globally unacceptable" in f.lower() for f in res.dominant_factors)


def test_boundary_confidence_exactly_at_threshold(now):
    """Verify confidence exactly at threshold is accepted without abstention."""
    # Target confidence = 0.50
    custom_cfg = ConfidenceConfig(confidence_threshold=0.50)
    evaluator = ConfidenceEvaluator(config=custom_cfg)

    # Craft synthetic provisional output
    prov = ProvisionalEstimationOutput(
        timestamp=now,
        candidate_state=FatigueState.NORMAL,
        provisional_score=None,
        dominant_factors=["Positive baseline concordance"],
        rule_evidence_trace={
            "rule_normal": {
                "hr_concordance_available": True,
                "rmssd_concordance_available": True,
                "physio_concordance_supported": True,
                "context_supported": True,
            }
        },
    )
    # Breakdown computes confidence; if confidence is >= 0.50, candidate is retained
    q = make_quality(now, overall_sqi=0.90, hr_sqi=0.90, rr_sqi=0.90)
    res = evaluator.evaluate(prov, quality=q)

    assert res.confidence >= 0.50
    assert res.fatigue_state == FatigueState.NORMAL


def test_boundary_confidence_just_below_threshold(now):
    """Verify confidence just below threshold forces abstention."""
    # Set threshold high enough that test telemetry is just below it
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context)
    q = make_quality(now, overall_sqi=0.70, hr_sqi=0.70, rr_sqi=0.70)

    # First observe natural confidence
    eval_base = ConfidenceEvaluator()
    base_conf = eval_base.evaluate(prov, quality=q).confidence

    # Now set threshold to base_conf + 0.001 (just above base_conf)
    custom_cfg = ConfidenceConfig(confidence_threshold=round(base_conf + 0.001, 4))
    eval_strict = ConfidenceEvaluator(config=custom_cfg)
    res = eval_strict.evaluate(prov, quality=q)

    assert res.confidence < custom_cfg.confidence_threshold
    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA
    assert any("confidence inadequate" in f.lower() for f in res.dominant_factors)


def test_boundary_confidence_exactly_zero(now):
    """Verify zero quality and missing telemetry yields exactly 0.0 confidence."""
    evaluator = ConfidenceEvaluator()
    prov = ProvisionalEstimationOutput(
        timestamp=now,
        candidate_state=FatigueState.INSUFFICIENT_DATA,
        provisional_score=None,
    )
    res = evaluator.evaluate(prov, quality=None)

    assert res.confidence == 0.0


def test_boundary_confidence_exactly_one(now):
    """Verify perfect telemetry and full evidence yields exactly 1.0 confidence."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context)

    q_perfect = make_quality(
        now,
        overall_sqi=1.0,
        hr_sqi=1.0,
        rr_sqi=1.0,
        accel_sqi=1.0,
        motion_corruption=0.0,
    )
    res = evaluator.evaluate(prov, quality=q_perfect, features=features, context=context)

    assert res.confidence == 1.0


def test_contradiction_in_trace_zeros_evidence_completeness(now):
    """Verify contradiction_detected=True in rule trace forces completeness score to 0.0."""
    prov_contradicted = ProvisionalEstimationOutput(
        timestamp=now,
        candidate_state=FatigueState.INSUFFICIENT_DATA,
        provisional_score=None,
        rule_evidence_trace={"contradiction_detected": True},
    )

    completeness = compute_evidence_completeness_score(prov_contradicted)

    assert completeness == 0.0


# =====================================================================
# 9. Provenance, Immutability & Contract Checks
# =====================================================================

def test_no_fabrication_or_imputation(now):
    """Verify missing accelerometer channel in quality assessment is not fabricated."""
    evaluator = ConfidenceEvaluator()
    quality_no_accel = QualityAssessment(
        timestamp=now,
        overall_sqi=0.80,
        is_telemetry_acceptable=True,
        channels={
            "heart_rate": ChannelQuality(channel_name="heart_rate", sqi_score=0.85, is_usable=True),
            "rr_interval": ChannelQuality(channel_name="rr_interval", sqi_score=0.85, is_usable=True),
        },
    )
    features = make_features(now, hr_dev=20.0, rmssd_ratio=0.85, activity=0.45)
    prov = get_step7_provisional(features, quality=quality_no_accel)

    breakdown = evaluator.compute_breakdown(prov, quality=quality_no_accel, features=features)

    assert "accelerometer" in breakdown.relied_channels
    assert breakdown.channel_quality_score < 0.50


def test_baseline_version_provenance_preserved(now):
    """Verify baseline version ID is carried from Step 7 through to EstimationMetadata."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=1.0, rmssd_ratio=0.95)
    context = OperationalContext(timestamp=now, external_g_load=1.0)
    prov = get_step7_provisional(features, context=context, baseline_version="PILOT-DELTA-2026-v2")

    res = evaluator.evaluate(prov, quality=make_quality(now), features=features, context=context)

    assert res.metadata.baseline_version_used == "PILOT-DELTA-2026-v2"


def test_input_immutability(now):
    """Verify provisional output, quality, features, and context are never mutated."""
    evaluator = ConfidenceEvaluator()
    features = make_features(now, hr_dev=15.0, rmssd_ratio=0.90)
    context = OperationalContext(timestamp=now, external_g_load=3.0)
    quality = make_quality(now, overall_sqi=0.90)
    prov = get_step7_provisional(features, context=context, quality=quality)

    _ = evaluator.evaluate(prov, quality=quality, features=features, context=context)

    assert prov.candidate_state == FatigueState.ELEVATED_WORKLOAD
    assert quality.overall_sqi == 0.90
    assert features.baseline_features.hr_deviation_from_baseline == 15.0
    assert context.external_g_load == 3.0


def test_provisional_score_strictly_remains_none(now):
    """Verify Option B compliance: fatigue_score is None across all states."""
    evaluator = ConfidenceEvaluator()
    quality = make_quality(now)

    # NORMAL
    prov_n = get_step7_provisional(make_features(now, hr_dev=1.0, rmssd_ratio=0.95), context=OperationalContext(timestamp=now, external_g_load=1.0))
    assert evaluator.evaluate(prov_n, quality=quality).fatigue_score is None

    # WORKLOAD
    prov_w = get_step7_provisional(make_features(now, hr_dev=20.0, rmssd_ratio=0.9), context=OperationalContext(timestamp=now, external_g_load=3.0))
    assert evaluator.evaluate(prov_w, quality=quality).fatigue_score is None

    # FATIGUE
    prov_f = get_step7_provisional(make_features(now, hr_dev=1.0, rmssd_ratio=0.5), context=OperationalContext(timestamp=now, mission_phase=MissionPhase.CRUISE))
    assert evaluator.evaluate(prov_f, quality=quality).fatigue_score is None

    # INSUFFICIENT_DATA
    prov_i = get_step7_provisional(make_features(now, hr_dev=None, rmssd_ratio=None, baseline_available=False))
    assert evaluator.evaluate(prov_i, quality=quality).fatigue_score is None


def test_no_step7_state_rules_duplicated_in_step8(now):
    """Verify Step 8 evaluates confidence purely from evidence presence, not re-checking physiological limits."""
    evaluator = ConfidenceEvaluator()
    prov_synthetic = ProvisionalEstimationOutput(
        timestamp=now,
        candidate_state=FatigueState.NORMAL,
        provisional_score=None,
        dominant_factors=["Positive baseline concordance"],
        rule_evidence_trace={
            "rule_normal": {
                "hr_concordance_available": True,
                "rmssd_concordance_available": True,
                "physio_concordance_supported": True,
                "context_supported": True,
            }
        },
        baseline_version_used="v1",
    )
    quality = make_quality(now, overall_sqi=0.90)

    res = evaluator.evaluate(prov_synthetic, quality=quality)
    assert res.fatigue_state == FatigueState.NORMAL
