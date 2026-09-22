"""Comprehensive Integration Tests for AeroVital Pipeline Orchestrator (Step 9).

Verifies the end-to-end execution of all 8 core stages:
Telemetry
  → Validation (Step 2)
  → Signal Quality (Step 3)
  → Preprocessing / Windowing (Step 4)
  → Feature Extraction (Step 5)
  → Pilot Baseline Normalization (Step 6)
  → State Estimation (Step 7)
  → Confidence & Final Result (Step 8)

Tests:
A. Complete valid telemetry sequence produces valid final result
B. Insufficient history produces no fabricated result (returns None)
C. Missing optional channels operates without failure
D. Invalid telemetry raises auditable validation exceptions
E. Poor signal quality causes appropriate abstention
F. Pilot baseline unavailable avoids fabricating comparisons and yields INSUFFICIENT_DATA
G. Baseline version provenance carried into final EstimationMetadata
H. FATIGUE path end-to-end
I. ELEVATED_WORKLOAD path end-to-end
J. NORMAL path end-to-end
K. INSUFFICIENT_DATA path end-to-end
L. Input, baseline, and context immutability
M. Determinism across identical runs
N. No Step 7 physiological rule duplication in pipeline.py
O. No Step 8 confidence formula duplication in pipeline.py
P. Dynamic baseline assignment and pipeline reset
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.context import MissionPhase, OperationalContext
from backend.core.schemas.result import FatigueEstimationResult, FatigueState
from backend.core.schemas.telemetry import TelemetrySample
from backend.core.validation.exceptions import (
    PhysiologicalPlausibilityError,
    NumericValueError,
    SignalValidationError,
)
from backend.core.quality import SignalQualityAssessor, QualityConfig, AccelUnit
from backend.core.pipeline import AeroVitalPipeline


# =====================================================================
# Fixtures & Helpers
# =====================================================================

@pytest.fixture
def base_time() -> datetime:
    """Fixed reference start timestamp."""
    return datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc)


def make_sample(
    ts: datetime,
    hr: float | None = 72.0,
    rr: list[float] | None = None,
    accel: tuple[float, float, float] | None = (0.0, 0.0, 1.0),
    spo2: float | None = 98.0,
    temp: float | None = 36.5,
) -> TelemetrySample:
    """Helper to generate a valid TelemetrySample."""
    rr_val = rr if rr is not None else [800.0, 850.0, 800.0, 850.0, 800.0]
    ax, ay, az = accel if accel is not None else (None, None, None)
    return TelemetrySample(
        timestamp=ts,
        heart_rate=hr,
        rr_interval=rr_val,
        spo2=spo2,
        skin_temperature=temp,
        accel_x=ax,
        accel_y=ay,
        accel_z=az,
    )


def make_baseline(
    pilot_id: str = "PILOT-007",
    version: str = "2026-Q3-v1",
    resting_hr: float = 70.0,
    resting_rmssd: float = 50.0,
) -> PilotBaseline:
    """Helper to generate a calibrated PilotBaseline."""
    return PilotBaseline(
        pilot_id=pilot_id,
        baseline_version=version,
        created_at=datetime(2026, 9, 1, 8, 0, 0, tzinfo=timezone.utc),
        resting_heart_rate=resting_hr,
        baseline_rmssd=resting_rmssd,
        is_calibrated=True,
    )


# =====================================================================
# Test A: Complete Valid Telemetry Sequence
# =====================================================================

def test_pipeline_complete_valid_sequence(base_time):
    """Verify feeding a sequence of valid samples produces valid FatigueEstimationResults."""
    baseline = make_baseline()
    pipeline = AeroVitalPipeline(baseline=baseline)
    context = OperationalContext(
        timestamp=base_time,
        external_g_load=1.0,
        mission_phase=MissionPhase.CRUISE,
    )

    # Generate 10 consecutive 1-second samples
    samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(10)]
    results = pipeline.process_sequence(samples, context=context)

    # With default min_samples_required=5, results should be emitted starting from sample 5
    assert len(results) == 6
    for res in results:
        assert isinstance(res, FatigueEstimationResult)
        assert res.fatigue_score is None  # Option B
        assert 0.0 <= res.confidence <= 1.0
        assert 0.0 <= res.overall_sqi <= 1.0
        assert res.metadata.baseline_version_used == baseline.baseline_version


# =====================================================================
# Test B: Insufficient History (No Fabricated Result)
# =====================================================================

def test_pipeline_insufficient_history_no_fabricated_result(base_time):
    """Verify no result is returned while buffer has insufficient samples."""
    pipeline = AeroVitalPipeline(baseline=make_baseline())

    # First sample: buffer has 1 sample (requires 5)
    s1 = make_sample(base_time)
    res1 = pipeline.process_sample(s1)
    assert res1 is None

    # Second sample: buffer has 2 samples
    s2 = make_sample(base_time + timedelta(seconds=1))
    res2 = pipeline.process_sample(s2)
    assert res2 is None

    # Third and fourth samples
    assert pipeline.process_sample(make_sample(base_time + timedelta(seconds=2))) is None
    assert pipeline.process_sample(make_sample(base_time + timedelta(seconds=3))) is None

    # Fifth sample: buffer now has 5 samples -> window is ready!
    res5 = pipeline.process_sample(make_sample(base_time + timedelta(seconds=4)))
    assert res5 is not None
    assert isinstance(res5, FatigueEstimationResult)


# =====================================================================
# Test C: Missing Optional Channels
# =====================================================================

def test_pipeline_missing_optional_channels_remains_functional(base_time):
    """Verify pipeline functions properly when optional channels (SpO2, skin temp, accel) are missing."""
    pipeline = AeroVitalPipeline(baseline=make_baseline())
    context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

    # Telemetry with only HR and RR (no accelerometer, no SpO2, no skin temp)
    samples = [
        make_sample(
            base_time + timedelta(seconds=i),
            accel=None,
            spo2=None,
            temp=None,
        )
        for i in range(6)
    ]

    results = pipeline.process_sequence(samples, context=context)
    assert len(results) == 2
    for r in results:
        assert isinstance(r, FatigueEstimationResult)
        assert r.confidence > 0.0


# =====================================================================
# Test D: Invalid Telemetry (Auditable Rejection)
# =====================================================================

def test_pipeline_invalid_telemetry_raises_and_is_auditable(base_time):
    """Verify invalid telemetry raises SignalValidationError and preserves engine integrity."""
    pipeline = AeroVitalPipeline(baseline=make_baseline())

    # Feed valid sample first
    s1 = make_sample(base_time)
    pipeline.process_sample(s1)

    # Feed invalid sample (heart_rate = -25.0 BPM)
    s_bad_hr = TelemetrySample(
        timestamp=base_time + timedelta(seconds=1),
        heart_rate=-25.0,
    )
    with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
        pipeline.process_sample(s_bad_hr)

    assert "heart rate" in str(exc_info.value).lower()
    # Buffer should still only contain the 1 valid sample
    assert pipeline.window_buffer.sample_count == 1

    # Feed invalid sample (NaN in heart rate)
    s_nan = TelemetrySample(
        timestamp=base_time + timedelta(seconds=2),
        heart_rate=float("nan"),
    )
    with pytest.raises(NumericValueError):
        pipeline.process_sample(s_nan)

    assert pipeline.window_buffer.sample_count == 1


# =====================================================================
# Test E: Poor Signal Quality Abstention
# =====================================================================

def test_pipeline_poor_signal_quality_abstains(base_time):
    """Verify telemetry with severe motion corruption causes engine to abstain."""
    qa = SignalQualityAssessor(config=QualityConfig(accel_unit=AccelUnit.G))
    pipeline = AeroVitalPipeline(baseline=make_baseline(), quality_assessor=qa)
    context = OperationalContext(timestamp=base_time, external_g_load=1.0)

    # Accelerometer readings with severe dynamic motion corruption (> 1.2g dynamic oscillation)
    samples = [
        make_sample(
            base_time + timedelta(seconds=i),
            hr=72.0,
            accel=(3.5, -2.8, 4.0),  # Extreme dynamic acceleration
        )
        for i in range(6)
    ]

    results = pipeline.process_sequence(samples, context=context)
    assert len(results) > 0
    latest_result = results[-1]

    # Because motion corruption is severe, channel reliability and confidence are suppressed
    assert latest_result.fatigue_state == FatigueState.INSUFFICIENT_DATA


# =====================================================================
# Test F: Pilot Baseline Unavailable
# =====================================================================

def test_pipeline_baseline_unavailable_does_not_fabricate(base_time):
    """Verify absence of baseline does not substitute population defaults and abstains."""
    # Pipeline without baseline
    pipeline = AeroVitalPipeline(baseline=None)
    context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

    samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(6)]
    results = pipeline.process_sequence(samples, context=context)

    assert len(results) > 0
    res = results[-1]
    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA
    assert res.metadata.baseline_version_used is None
    assert any("baseline unavailable" in f.lower() for f in res.dominant_factors)


# =====================================================================
# Test G: Baseline Version Provenance
# =====================================================================

def test_pipeline_baseline_version_provenance(base_time):
    """Verify baseline version ID is carried all the way to final EstimationMetadata."""
    baseline = make_baseline(pilot_id="PILOT-VIPER", version="2026-OCT-v4.2")
    pipeline = AeroVitalPipeline(baseline=baseline)
    context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

    samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(6)]
    results = pipeline.process_sequence(samples, context=context)

    assert len(results) > 0
    assert results[-1].metadata.baseline_version_used == "2026-OCT-v4.2"


# =====================================================================
# Test H: FATIGUE Path End-to-End
# =====================================================================

def test_pipeline_fatigue_path_end_to_end(base_time):
    """Verify end-to-end execution of autonomic fatigue pattern reaching final FATIGUE state."""
    # Calibrated baseline with resting HR 70 BPM, resting RMSSD 55 ms
    baseline = make_baseline(resting_hr=70.0, resting_rmssd=55.0)
    pipeline = AeroVitalPipeline(baseline=baseline)
    context = OperationalContext(
        timestamp=base_time,
        external_g_load=1.0,  # Confirmed low G
        mission_phase=MissionPhase.CRUISE,  # Confirmed benign phase
    )

    # Telemetry with nominal HR (71 BPM) but depressed beat-to-beat variability (RMSSD ~15ms, ratio ~0.27 < 0.70)
    # Consecutive RR intervals: [850, 860, 850, 860] -> diffs are 10ms -> RMSSD = 10.0 ms
    samples = [
        make_sample(
            base_time + timedelta(seconds=i),
            hr=71.0,
            rr=[850.0, 860.0, 850.0, 860.0, 850.0],
            accel=(0.0, 0.0, 1.0),
        )
        for i in range(8)
    ]

    results = pipeline.process_sequence(samples, context=context)
    assert len(results) > 0
    res = results[-1]

    assert res.fatigue_state == FatigueState.FATIGUE
    assert res.confidence >= 0.40
    assert any("Depressed beat-to-beat variability" in f for f in res.dominant_factors)
    assert any("CRUISE" in f or "Confirmed low G-load" in f for f in res.dominant_factors)


# =====================================================================
# Test I: ELEVATED_WORKLOAD Path End-to-End
# =====================================================================

def test_pipeline_elevated_workload_path_end_to_end(base_time):
    """Verify end-to-end execution of elevated workload pattern reaching final ELEVATED_WORKLOAD."""
    baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
    pipeline = AeroVitalPipeline(baseline=baseline)
    # High workload context: 3.5g load
    context = OperationalContext(
        timestamp=base_time,
        external_g_load=3.5,
    )

    # Telemetry with elevated HR (95.0 BPM -> delta HR = +25.0 BPM > 10.0 threshold)
    samples = [
        make_sample(
            base_time + timedelta(seconds=i),
            hr=95.0,
            rr=[630.0, 635.0, 630.0, 635.0],
            accel=(0.0, 0.0, 1.0),
        )
        for i in range(8)
    ]

    results = pipeline.process_sequence(samples, context=context)
    assert len(results) > 0
    res = results[-1]

    assert res.fatigue_state == FatigueState.ELEVATED_WORKLOAD
    assert res.confidence >= 0.40
    assert any("High G-load" in f for f in res.dominant_factors)
    assert any("Elevated heart rate" in f for f in res.dominant_factors)


# =====================================================================
# Test J: NORMAL Path End-to-End
# =====================================================================

def test_pipeline_normal_path_end_to_end(base_time):
    """Verify end-to-end execution of nominal baseline concordance reaching final NORMAL."""
    baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
    pipeline = AeroVitalPipeline(baseline=baseline)
    context = OperationalContext(
        timestamp=base_time,
        external_g_load=1.0,
        mission_phase=MissionPhase.CRUISE,
    )

    # Telemetry with nominal HR (72.0 BPM -> delta +2.0 BPM) and nominal RMSSD (~48ms -> ratio 0.96 >= 0.85)
    # Successive diffs around 45-50ms
    samples = [
        make_sample(
            base_time + timedelta(seconds=i),
            hr=72.0,
            rr=[800.0, 850.0, 800.0, 850.0, 800.0],
            accel=(0.0, 0.0, 1.0),
        )
        for i in range(8)
    ]

    results = pipeline.process_sequence(samples, context=context)
    assert len(results) > 0
    res = results[-1]

    assert res.fatigue_state == FatigueState.NORMAL
    assert res.confidence >= 0.40
    assert any("Positive baseline concordance" in f for f in res.dominant_factors)


# =====================================================================
# Test K: INSUFFICIENT_DATA Path End-to-End
# =====================================================================

def test_pipeline_insufficient_data_path_end_to_end(base_time):
    """Verify low RMSSD without benign operational context abstains to INSUFFICIENT_DATA."""
    baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
    pipeline = AeroVitalPipeline(baseline=baseline)
    # Operational context is completely missing (None)
    context = None

    # Low RMSSD, but operational context is unverified
    samples = [
        make_sample(
            base_time + timedelta(seconds=i),
            hr=71.0,
            rr=[850.0, 860.0, 850.0, 860.0],
        )
        for i in range(6)
    ]

    results = pipeline.process_sequence(samples, context=context)
    assert len(results) > 0
    res = results[-1]

    # Must abstain because fatigue context was unverified
    assert res.fatigue_state == FatigueState.INSUFFICIENT_DATA
    assert any("unverified by operational context" in f for f in res.dominant_factors)


# =====================================================================
# Test L: Immutability
# =====================================================================

def test_pipeline_no_mutation(base_time):
    """Verify incoming TelemetrySamples, context, and baseline remain strictly unmutated."""
    baseline = make_baseline()
    pipeline = AeroVitalPipeline(baseline=baseline)
    context = OperationalContext(timestamp=base_time, external_g_load=2.0)
    sample = make_sample(base_time)

    _ = pipeline.process_sample(sample, context=context)

    assert sample.heart_rate == 72.0
    assert context.external_g_load == 2.0
    assert baseline.resting_heart_rate == 70.0
    assert baseline.is_calibrated is True


# =====================================================================
# Test M: Determinism
# =====================================================================

def test_pipeline_determinism(base_time):
    """Verify two independent pipeline instances given identical data produce identical results."""
    baseline1 = make_baseline()
    baseline2 = make_baseline()

    pipe1 = AeroVitalPipeline(baseline=baseline1)
    pipe2 = AeroVitalPipeline(baseline=baseline2)

    context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
    samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(8)]

    results1 = pipe1.process_sequence(samples, context=context)
    results2 = pipe2.process_sequence(samples, context=context)

    assert len(results1) == len(results2)
    for r1, r2 in zip(results1, results2):
        assert r1.fatigue_state == r2.fatigue_state
        assert r1.confidence == r2.confidence
        assert r1.overall_sqi == r2.overall_sqi
        assert r1.dominant_factors == r2.dominant_factors
        assert r1.metadata == r2.metadata


# =====================================================================
# Test N: No Step 7 Logic Duplication
# =====================================================================

def test_pipeline_no_step7_logic_duplication():
    """Verify pipeline.py contains zero physiological threshold constants or fatigue rule logic."""
    pipeline_file = Path(__file__).parent.parent / "pipeline" / "pipeline.py"
    source = pipeline_file.read_text()

    # Step 7 specific configuration constants that must NEVER appear in orchestrator
    forbidden_tokens = [
        "hr_deviation_workload_threshold",
        "rmssd_ratio_fatigue_threshold",
        "hr_deviation_nominal_max",
        "rmssd_ratio_nominal_min",
        "g_load_workload_threshold",
        "g_load_nominal_max",
        "activity_workload_threshold",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"Forbidden Step 7 token '{token}' duplicated in pipeline.py"


# =====================================================================
# Test O: No Step 8 Logic Duplication
# =====================================================================

def test_pipeline_no_step8_logic_duplication():
    """Verify pipeline.py contains zero confidence weights or SQI aggregation formulas."""
    pipeline_file = Path(__file__).parent.parent / "pipeline" / "pipeline.py"
    source = pipeline_file.read_text()

    # Step 8 specific configuration constants and calculation tokens that must NEVER appear in orchestrator
    forbidden_tokens = [
        "weight_global_sqi",
        "weight_channel_quality",
        "weight_evidence_completeness",
        "weight_motion_integrity",
        "compute_breakdown",
        "compute_global_sqi_score",
        "compute_motion_integrity_score",
        "unacceptable_telemetry_cap",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"Forbidden Step 8 token '{token}' duplicated in pipeline.py"


# =====================================================================
# Test P: Dynamic Operations (Set Baseline & Reset)
# =====================================================================

def test_pipeline_dynamic_operations(base_time):
    """Verify setting baseline dynamically and resetting pipeline state."""
    pipeline = AeroVitalPipeline(baseline=None)
    assert pipeline.get_baseline() is None

    # Feed 6 samples without baseline -> INSUFFICIENT_DATA
    samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(6)]
    res = pipeline.process_sequence(samples)
    assert res[-1].fatigue_state == FatigueState.INSUFFICIENT_DATA

    # Dynamically attach calibrated baseline
    new_baseline = make_baseline(version="DYNAMIC-v1")
    pipeline.set_baseline(new_baseline)
    assert pipeline.get_baseline() == new_baseline

    # Reset buffer
    pipeline.reset()
    assert pipeline.window_buffer.sample_count == 0

    # Feed samples again -> now uses the new baseline!
    res_after = pipeline.process_sequence(samples, context=OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE))
    assert res_after[-1].metadata.baseline_version_used == "DYNAMIC-v1"


def test_pipeline_process_window_samples_direct(base_time):
    """Verify direct batch window processing via process_window_samples."""
    pipeline = AeroVitalPipeline(baseline=make_baseline())
    context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

    # Direct 6-sample window batch
    window_samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(6)]
    result = pipeline.process_window_samples(window_samples, context=context)

    assert isinstance(result, FatigueEstimationResult)
    assert result.fatigue_state == FatigueState.NORMAL

    # Trying with fewer samples than min_samples_required raises ValueError
    with pytest.raises(ValueError) as exc_info:
        pipeline.process_window_samples(window_samples[:2])
    assert "insufficient sample history" in str(exc_info.value).lower()
