"""System-Level Verification of the AeroVital Core Engine (Step 10).

Verifies the COMPLETE framework-independent AeroVital core engine as a unified system:
TelemetrySample stream
        ↓
Validation (Step 2)
        ↓
Signal Quality (Step 3)
        ↓
Preprocessing / Windowing (Step 4)
        ↓
Feature Extraction (Step 5)
        ↓
Pilot Baseline Normalization (Step 6)
        ↓
Provisional State Estimation (Step 7)
        ↓
Confidence & Abstention (Step 8)
        ↓
Pipeline Coordination (Step 9)
        ↓
FatigueEstimationResult

IMPORTANT DISCLAIMER:
All telemetry and flight scenarios in this test suite are deterministic synthetic
engineering fixtures constructed strictly for software verification. None represent
medically, clinically, physiologically, or aviation-certified data or state conclusions.
"""

from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import pytest

from backend.core.baseline.normalizer import BaselineNormalizer
from backend.core.confidence.config import ConfidenceConfig
from backend.core.confidence.evaluator import ConfidenceEvaluator
from backend.core.features.extractor import FeatureExtractor
from backend.core.intelligence.config import EstimatorConfig
from backend.core.intelligence.estimator import ProvisionalRuleBasedEstimator
from backend.core.pipeline import AeroVitalPipeline
from backend.core.preprocessing.windowing import WindowBuffer, WindowConfig
from backend.core.quality import AccelUnit, QualityConfig, SignalQualityAssessor
from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.context import MissionPhase, OperationalContext
from backend.core.schemas.result import FatigueEstimationResult, FatigueState
from backend.core.schemas.telemetry import TelemetrySample
from backend.core.validation.exceptions import (
    NumericValueError,
    PhysiologicalPlausibilityError,
    SignalValidationError,
    TimestampMonotonicityError,
)
from backend.core.validation.validator import TelemetryValidator


# =====================================================================
# Fixtures & Synthetic Data Helpers
# =====================================================================

@pytest.fixture
def base_time() -> datetime:
    """Fixed reference start timestamp for deterministic testing."""
    return datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc)


_DEFAULT = object()


def make_sample(
    ts: datetime,
    hr: float | None | object = _DEFAULT,
    rr: list[float] | None | object = _DEFAULT,
    accel: tuple[float, float, float] | None | object = _DEFAULT,
    spo2: float | None | object = _DEFAULT,
    temp: float | None | object = _DEFAULT,
) -> TelemetrySample:
    """Deterministic synthetic TelemetrySample generator."""
    hr_val = 70.0 if hr is _DEFAULT else hr
    rr_val = [800.0, 850.0, 800.0, 850.0, 800.0] if rr is _DEFAULT else rr
    accel_val = (0.0, 0.0, 1.0) if accel is _DEFAULT else accel
    spo2_val = 98.0 if spo2 is _DEFAULT else spo2
    temp_val = 36.5 if temp is _DEFAULT else temp

    ax, ay, az = accel_val if accel_val is not None else (None, None, None)
    return TelemetrySample(
        timestamp=ts,
        heart_rate=hr_val,
        rr_interval=rr_val,
        spo2=spo2_val,
        skin_temperature=temp_val,
        accel_x=ax,
        accel_y=ay,
        accel_z=az,
    )


def make_baseline(
    pilot_id: str = "TEST-PILOT-01",
    version: str = "2026-Q3-v1",
    resting_hr: float = 70.0,
    resting_rmssd: float = 50.0,
) -> PilotBaseline:
    """Deterministic calibrated PilotBaseline fixture."""
    return PilotBaseline(
        pilot_id=pilot_id,
        baseline_version=version,
        created_at=datetime(2026, 9, 1, 8, 0, 0, tzinfo=timezone.utc),
        resting_heart_rate=resting_hr,
        baseline_rmssd=resting_rmssd,
        is_calibrated=True,
    )


# =====================================================================
# 3. End-to-End Scenarios (A through P)
# =====================================================================

class TestEndToEndScenarios:
    """Core verification of system-level operational scenarios."""

    def test_scenario_a_normal_flight(self, base_time):
        """Scenario A: Pilot baseline available, concordant physiology, benign flight context -> NORMAL."""
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
        pipeline = AeroVitalPipeline(baseline=baseline)
        context = OperationalContext(
            timestamp=base_time,
            external_g_load=1.0,
            mission_phase=MissionPhase.CRUISE,
        )

        # 8 samples with nominal HR (71 BPM, +1 dev) and nominal RMSSD (~50ms, ratio ~1.0)
        samples = [make_sample(base_time + timedelta(seconds=i), hr=71.0) for i in range(8)]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        assert latest.fatigue_state == FatigueState.NORMAL
        assert latest.confidence >= 0.40
        assert latest.overall_sqi >= 0.40
        assert latest.fatigue_score is None  # Option B invariant
        assert any("Positive baseline concordance" in f for f in latest.dominant_factors)

    def test_scenario_b_elevated_workload(self, base_time):
        """Scenario B: Physiological activation + positive workload context -> ELEVATED_WORKLOAD."""
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
        pipeline = AeroVitalPipeline(baseline=baseline)
        context = OperationalContext(
            timestamp=base_time,
            external_g_load=3.5,  # High G-load
            mission_phase=MissionPhase.COMBAT_MANEUVER,
        )

        # Elevated HR (+25 BPM deviation over baseline 70)
        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=95.0,
                rr=[630.0, 635.0, 630.0, 635.0],
            )
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        assert latest.fatigue_state == FatigueState.ELEVATED_WORKLOAD
        assert latest.confidence >= 0.40
        assert latest.fatigue_score is None
        assert any("High G-load" in f for f in latest.dominant_factors)
        assert any("Elevated heart rate" in f for f in latest.dominant_factors)

    def test_scenario_c_fatigue_pattern(self, base_time):
        """Scenario C: Pilot-relative RMSSD degradation + benign flight context -> FATIGUE."""
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=55.0)
        pipeline = AeroVitalPipeline(baseline=baseline)
        context = OperationalContext(
            timestamp=base_time,
            external_g_load=1.0,  # Confirmed low G
            mission_phase=MissionPhase.CRUISE,  # Confirmed benign phase
        )

        # Depressed beat-to-beat variability (diffs 10ms -> RMSSD 10ms, ratio 10/55 = 0.18 < 0.70)
        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=71.0,
                rr=[850.0, 860.0, 850.0, 860.0, 850.0],
            )
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        assert latest.fatigue_state == FatigueState.FATIGUE
        assert latest.confidence >= 0.40
        assert latest.fatigue_score is None
        assert any("Depressed beat-to-beat variability" in f for f in latest.dominant_factors)
        assert any("CRUISE" in f or "Confirmed low G-load" in f for f in latest.dominant_factors)

    def test_scenario_d_low_rmssd_plus_high_workload_contradiction(self, base_time):
        """Scenario D: Reduced RMSSD while acute workload context is present -> INSUFFICIENT_DATA (no winner invented)."""
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=55.0)
        pipeline = AeroVitalPipeline(baseline=baseline)
        # Acute workload context (3.5g load)
        context = OperationalContext(
            timestamp=base_time,
            external_g_load=3.5,
        )

        # Reduced RMSSD (10ms, ratio ~0.18) with nominal HR (71 BPM, not elevated)
        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=71.0,
                rr=[850.0, 860.0, 850.0, 860.0, 850.0],
            )
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        # In Step 7: Workload rule fails because HR is not elevated (+1.0 <= 10.0).
        # Fatigue rule fails because high G-load (3.5g) is contradictory and acute strain prevents benign context.
        # Normal rule fails because RMSSD is degraded and acute strain is present.
        # Therefore, candidate is strictly INSUFFICIENT_DATA.
        assert latest.fatigue_state == FatigueState.INSUFFICIENT_DATA
        assert latest.fatigue_score is None

    def test_scenario_e_low_rmssd_no_benign_context(self, base_time):
        """Scenario E: Reduced RMSSD but flight context unavailable -> INSUFFICIENT_DATA (no assumed benignity)."""
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=55.0)
        pipeline = AeroVitalPipeline(baseline=baseline)
        # Operational context completely missing
        context = None

        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=71.0,
                rr=[850.0, 860.0, 850.0, 860.0, 850.0],
            )
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        assert latest.fatigue_state == FatigueState.INSUFFICIENT_DATA
        assert any("unverified by operational context" in f for f in latest.dominant_factors)

    def test_scenario_f_missing_rr(self, base_time):
        """Scenario F: HR available but RR missing -> no HRV fabrication, FATIGUE impossible -> INSUFFICIENT_DATA."""
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
        pipeline = AeroVitalPipeline(baseline=baseline)
        context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

        # RR is None
        samples = [
            make_sample(base_time + timedelta(seconds=i), hr=72.0, rr=None)
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        assert latest.fatigue_state != FatigueState.FATIGUE
        assert latest.fatigue_state == FatigueState.INSUFFICIENT_DATA

    def test_scenario_g_missing_hr(self, base_time):
        """Scenario G: RR available but HR missing -> no HR activation fabrication, ELEVATED_WORKLOAD impossible."""
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
        pipeline = AeroVitalPipeline(baseline=baseline)
        context = OperationalContext(timestamp=base_time, external_g_load=3.5, mission_phase=MissionPhase.COMBAT_MANEUVER)

        # HR is None
        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=None,
                rr=[600.0, 605.0, 600.0, 605.0],
            )
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        # Cannot infer ELEVATED_WORKLOAD without HR activation
        assert latest.fatigue_state != FatigueState.ELEVATED_WORKLOAD
        assert latest.fatigue_state == FatigueState.INSUFFICIENT_DATA

    def test_scenario_h_missing_g_load(self, base_time):
        """Scenario H: RMSSD degradation, G-load unavailable, mission phase unverified -> INSUFFICIENT_DATA."""
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=55.0)
        pipeline = AeroVitalPipeline(baseline=baseline)
        # Context with no G-load and non-benign phase
        context = OperationalContext(
            timestamp=base_time,
            external_g_load=None,
            mission_phase=None,
        )

        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=71.0,
                rr=[850.0, 860.0, 850.0, 860.0, 850.0],
            )
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        # Must not fabricate a nominal 1.0g G-load
        assert latest.fatigue_state == FatigueState.INSUFFICIENT_DATA

    def test_scenario_i_sensor_quality_failure(self, base_time):
        """Scenario I: Severe motion corruption -> global quality/confidence abstention -> INSUFFICIENT_DATA."""
        qa = SignalQualityAssessor(config=QualityConfig(accel_unit=AccelUnit.G))
        pipeline = AeroVitalPipeline(baseline=make_baseline(), quality_assessor=qa)
        context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

        # Severe dynamic acceleration > 1.20g
        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=72.0,
                accel=(3.5, -2.8, 4.0),
            )
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        assert latest.fatigue_state == FatigueState.INSUFFICIENT_DATA

    def test_scenario_j_invalid_telemetry_rejection(self, base_time):
        """Scenario J: Injected invalid samples raise auditable errors and never enter window buffer."""
        pipeline = AeroVitalPipeline(baseline=make_baseline())

        # Valid initial sample
        s_valid = make_sample(base_time)
        pipeline.process_sample(s_valid)
        assert pipeline.window_buffer.sample_count == 1

        # 1. NaN in heart rate
        with pytest.raises(NumericValueError):
            pipeline.process_sample(TelemetrySample(timestamp=base_time + timedelta(seconds=1), heart_rate=float("nan")))
        assert pipeline.window_buffer.sample_count == 1

        # 2. Infinity in heart rate
        with pytest.raises(NumericValueError):
            pipeline.process_sample(TelemetrySample(timestamp=base_time + timedelta(seconds=2), heart_rate=float("inf")))
        assert pipeline.window_buffer.sample_count == 1

        # 3. Out-of-range HR (below plausible minimum 30 BPM)
        with pytest.raises(PhysiologicalPlausibilityError):
            pipeline.process_sample(TelemetrySample(timestamp=base_time + timedelta(seconds=3), heart_rate=25.0))
        assert pipeline.window_buffer.sample_count == 1

        # 4. Out-of-range HR (above plausible maximum 240 BPM)
        with pytest.raises(PhysiologicalPlausibilityError):
            pipeline.process_sample(TelemetrySample(timestamp=base_time + timedelta(seconds=4), heart_rate=250.0))
        assert pipeline.window_buffer.sample_count == 1

        # 5. Invalid RR interval (< 250ms or > 2500ms)
        with pytest.raises(PhysiologicalPlausibilityError):
            pipeline.process_sample(TelemetrySample(timestamp=base_time + timedelta(seconds=5), rr_interval=[100.0]))
        assert pipeline.window_buffer.sample_count == 1

        # 6. Invalid SpO2 (> 100% or < 50%)
        with pytest.raises(PhysiologicalPlausibilityError):
            pipeline.process_sample(TelemetrySample(timestamp=base_time + timedelta(seconds=6), spo2=105.0))
        assert pipeline.window_buffer.sample_count == 1

    def test_scenario_k_baseline_unavailable(self, base_time):
        """Scenario K: No baseline supplied -> no population defaults fabricated -> INSUFFICIENT_DATA."""
        pipeline = AeroVitalPipeline(baseline=None)
        context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

        samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(8)]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        assert latest.fatigue_state == FatigueState.INSUFFICIENT_DATA
        assert latest.metadata.baseline_version_used is None
        assert any("baseline unavailable" in f.lower() for f in latest.dominant_factors)

    def test_scenario_l_baseline_version_provenance(self, base_time):
        """Scenario L: Baseline version 'TEST-BASELINE-001' preserved through to final result metadata."""
        baseline = make_baseline(pilot_id="PILOT-ALPHA", version="TEST-BASELINE-001")
        pipeline = AeroVitalPipeline(baseline=baseline)
        context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

        samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(8)]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        assert results[-1].metadata.baseline_version_used == "TEST-BASELINE-001"

    def test_scenario_m_optional_sensor_dropout(self, base_time):
        """Scenario M: Optional channels (SpO2, skin temp, accel) dropped -> engine remains fully functional."""
        pipeline = AeroVitalPipeline(baseline=make_baseline())
        context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

        # Strip all optional channels
        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=71.0,
                rr=[800.0, 850.0, 800.0, 850.0, 800.0],
                accel=None,
                spo2=None,
                temp=None,
            )
            for i in range(8)
        ]
        results = pipeline.process_sequence(samples, context=context)

        assert len(results) > 0
        latest = results[-1]
        assert latest.fatigue_state == FatigueState.NORMAL
        assert latest.confidence >= 0.40

    def test_scenario_n_timestamp_and_stream_integrity(self, base_time):
        """Scenario N: Verify timestamp integrity contracts (strictly increasing, duplicate, retrograde, gaps)."""
        pipeline = AeroVitalPipeline(baseline=make_baseline())

        # 1. Strictly increasing timestamps pass
        pipeline.process_sample(make_sample(base_time))
        pipeline.process_sample(make_sample(base_time + timedelta(seconds=1)))
        assert pipeline.window_buffer.sample_count == 2

        # 2. Duplicate timestamp fails
        with pytest.raises(TimestampMonotonicityError):
            pipeline.process_sample(make_sample(base_time + timedelta(seconds=1)))

        # 3. Retrograde timestamp fails
        with pytest.raises(TimestampMonotonicityError):
            pipeline.process_sample(make_sample(base_time + timedelta(milliseconds=500)))

        # 4. Irregular but acceptable timing passes (e.g. 1.2s, 0.9s intervals)
        pipeline.process_sample(make_sample(base_time + timedelta(seconds=2, milliseconds=200)))
        pipeline.process_sample(make_sample(base_time + timedelta(seconds=3, milliseconds=100)))
        assert pipeline.window_buffer.sample_count == 4

        # 5. Large temporal gap: handled cleanly by windowing without crashing
        res = pipeline.process_sample(make_sample(base_time + timedelta(seconds=35)))
        # WindowBuffer evicts older samples beyond window_size_sec or retains valid sliding bounds
        assert pipeline.window_buffer.sample_count >= 1

    def test_scenario_o_multi_sortie_reset_isolation(self, base_time):
        """Scenario O: Session 1 followed by pipeline.reset() leaves no residual state for Session 2."""
        pipeline = AeroVitalPipeline(baseline=make_baseline(version="SORTIE-01"))
        context1 = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

        # Sortie 1
        samples1 = [make_sample(base_time + timedelta(seconds=i), hr=71.0) for i in range(8)]
        results1 = pipeline.process_sequence(samples1, context=context1)
        assert len(results1) > 0
        assert results1[-1].metadata.baseline_version_used == "SORTIE-01"

        # RESET
        pipeline.reset()
        assert pipeline.window_buffer.sample_count == 0
        assert pipeline._last_sample_timestamp is None
        assert pipeline._last_context_timestamp is None

        # Sortie 2: Can use earlier timestamp or different baseline without collision
        t_sortie2 = datetime(2026, 9, 23, 8, 0, 0, tzinfo=timezone.utc)
        pipeline.set_baseline(make_baseline(version="SORTIE-02"))
        context2 = OperationalContext(timestamp=t_sortie2, external_g_load=3.5, mission_phase=MissionPhase.COMBAT_MANEUVER)

        samples2 = [
            make_sample(t_sortie2 + timedelta(seconds=i), hr=95.0, rr=[630.0, 635.0, 630.0, 635.0])
            for i in range(8)
        ]
        results2 = pipeline.process_sequence(samples2, context=context2)
        assert len(results2) > 0
        assert results2[-1].fatigue_state == FatigueState.ELEVATED_WORKLOAD
        assert results2[-1].metadata.baseline_version_used == "SORTIE-02"

    def test_scenario_p_pilot_isolation(self, base_time):
        """Scenario P: Distinct pilot baselines evaluated on identical physiology produce pilot-specific results."""
        # Pilot A: High baseline resting HR (90 BPM), low RMSSD (25 ms)
        baseline_a = make_baseline(pilot_id="PILOT-A", resting_hr=90.0, resting_rmssd=25.0)
        pipe_a = AeroVitalPipeline(baseline=baseline_a)

        # Pilot B: Low baseline resting HR (60 BPM), high RMSSD (70 ms)
        baseline_b = make_baseline(pilot_id="PILOT-B", resting_hr=60.0, resting_rmssd=70.0)
        pipe_b = AeroVitalPipeline(baseline=baseline_b)

        # Test telemetry: HR = 88.0 BPM, RMSSD ~ 25.0 ms
        # For Pilot A: HR 88 is nominal (delta -2 BPM), RMSSD 25 is nominal (ratio 1.0) -> NORMAL
        # For Pilot B: HR 88 is activated (delta +28 BPM > 10.0), RMSSD 25 is depressed (ratio 0.35) -> NOT NORMAL
        context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
        samples = [
            make_sample(
                base_time + timedelta(seconds=i),
                hr=88.0,
                rr=[700.0, 725.0, 700.0, 725.0],
            )
            for i in range(8)
        ]

        res_a = pipe_a.process_sequence(samples, context=context)
        res_b = pipe_b.process_sequence(samples, context=context)

        assert len(res_a) > 0 and len(res_b) > 0
        assert res_a[-1].fatigue_state == FatigueState.NORMAL
        assert res_b[-1].fatigue_state != FatigueState.NORMAL


# =====================================================================
# 4. Longer Multi-Window Streaming Flight Test
# =====================================================================

def test_longer_multi_window_streaming_sequence(base_time):
    """Verify continuous multi-window flight sequence with shifting flight conditions.
    
    Phases:
    Window 1 (t=0..9s): Cruise, nominal HR 71 BPM, nominal RMSSD 50ms -> NORMAL
    Window 2 (t=10..19s): Combat maneuvering, elevated HR 95 BPM, 3.5g load -> ELEVATED_WORKLOAD
    Window 3 (t=20..29s): Cruise, low RMSSD 10ms, 1.0g load -> FATIGUE
    """
    baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
    # Configure 10-second rolling window duration so phases slide out cleanly
    buf = WindowBuffer(config=WindowConfig(window_duration_sec=10.0, min_samples_required=5))
    pipeline = AeroVitalPipeline(baseline=baseline, window_buffer=buf)

    # 1. Cruise nominal phase (10 seconds)
    samples_phase1 = [
        make_sample(base_time + timedelta(seconds=i), hr=71.0)
        for i in range(10)
    ]
    ctx1 = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
    res_phase1 = pipeline.process_sequence(samples_phase1, context=ctx1)
    assert len(res_phase1) == 6  # samples 5..9
    assert res_phase1[-1].fatigue_state == FatigueState.NORMAL

    # 2. Combat maneuvering high-workload phase (10 seconds)
    samples_phase2 = [
        make_sample(
            base_time + timedelta(seconds=10 + i),
            hr=95.0,
            rr=[630.0, 635.0, 630.0, 635.0],
        )
        for i in range(10)
    ]
    ctx2 = OperationalContext(timestamp=base_time + timedelta(seconds=10), external_g_load=3.5, mission_phase=MissionPhase.COMBAT_MANEUVER)
    res_phase2 = pipeline.process_sequence(samples_phase2, context=ctx2)
    assert len(res_phase2) == 10
    assert res_phase2[-1].fatigue_state == FatigueState.ELEVATED_WORKLOAD

    # 3. Autonomic fatigue pattern in cruise (10 seconds)
    samples_phase3 = [
        make_sample(
            base_time + timedelta(seconds=20 + i),
            hr=71.0,
            rr=[850.0, 860.0, 850.0, 860.0, 850.0],
        )
        for i in range(10)
    ]
    ctx3 = OperationalContext(timestamp=base_time + timedelta(seconds=20), external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
    res_phase3 = pipeline.process_sequence(samples_phase3, context=ctx3)
    assert len(res_phase3) == 10
    assert res_phase3[-1].fatigue_state == FatigueState.FATIGUE


# =====================================================================
# 5. Context Timestamp Behavior Verification
# =====================================================================

class TestContextTimestampHandling:
    """Rigorous verification of streaming operational context timestamp handling."""

    def test_same_context_timestamp_reused_across_samples(self, base_time):
        """1. Reusing same valid context across advancing samples behaves as intended."""
        pipeline = AeroVitalPipeline(baseline=make_baseline())
        context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

        # 6 samples with the exact same context object
        samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(6)]
        for s in samples:
            # Must not raise TimestampMonotonicityError
            res = pipeline.process_sample(s, context=context)
        assert res is not None

    def test_genuinely_retrograde_context_timestamp_rejected(self, base_time):
        """2. Genuinely retrograde context timestamp is rejected with TimestampMonotonicityError."""
        pipeline = AeroVitalPipeline(baseline=make_baseline())

        # Sample 1 at t=0s with context at t=10s
        c1 = OperationalContext(timestamp=base_time + timedelta(seconds=10), external_g_load=1.0)
        pipeline.process_sample(make_sample(base_time), context=c1)

        # Sample 2 at t=1s with context at t=5s (retrograde relative to c1)
        c2 = OperationalContext(timestamp=base_time + timedelta(seconds=5), external_g_load=1.0)
        with pytest.raises(TimestampMonotonicityError):
            pipeline.process_sample(make_sample(base_time + timedelta(seconds=1)), context=c2)

    def test_context_cannot_bypass_telemetry_timestamp_validation(self, base_time):
        """3. Context timestamp behavior cannot silently bypass telemetry timestamp validation."""
        pipeline = AeroVitalPipeline(baseline=make_baseline())
        c_advancing = OperationalContext(timestamp=base_time + timedelta(seconds=10), external_g_load=1.0)

        # First sample at t=0s
        pipeline.process_sample(make_sample(base_time), context=c_advancing)

        # Second sample with retrograde telemetry timestamp at t=-1s, even with advancing context
        with pytest.raises(TimestampMonotonicityError):
            pipeline.process_sample(
                make_sample(base_time - timedelta(seconds=1)),
                context=OperationalContext(timestamp=base_time + timedelta(seconds=20)),
            )

    def test_context_handling_does_not_alter_inference(self, base_time):
        """4. Context handling cleanly preserves workload and fatigue inference parameters."""
        pipeline = AeroVitalPipeline(baseline=make_baseline(resting_hr=70.0))
        # Verify high G context triggers workload
        c_high_g = OperationalContext(timestamp=base_time, external_g_load=4.0)
        samples = [
            make_sample(base_time + timedelta(seconds=i), hr=95.0, rr=[630.0, 635.0, 630.0, 635.0])
            for i in range(8)
        ]
        res = pipeline.process_sequence(samples, context=c_high_g)
        assert res[-1].fatigue_state == FatigueState.ELEVATED_WORKLOAD


# =====================================================================
# 6. Determinism Across Replay Runs
# =====================================================================

def test_determinism_across_replays(base_time):
    """Verify identical inputs through independent pipelines produce bit-for-bit identical results."""
    for repetition in range(3):
        baseline1 = make_baseline(version=f"REP-{repetition}")
        baseline2 = make_baseline(version=f"REP-{repetition}")

        pipe1 = AeroVitalPipeline(baseline=baseline1)
        pipe2 = AeroVitalPipeline(baseline=baseline2)

        context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
        samples = [make_sample(base_time + timedelta(seconds=i), hr=71.0) for i in range(8)]

        res1 = pipe1.process_sequence(samples, context=context)
        res2 = pipe2.process_sequence(samples, context=context)

        assert len(res1) == len(res2)
        for r1, r2 in zip(res1, res2):
            assert r1.timestamp == r2.timestamp
            assert r1.fatigue_state == r2.fatigue_state
            assert r1.confidence == r2.confidence
            assert r1.overall_sqi == r2.overall_sqi
            assert r1.dominant_factors == r2.dominant_factors
            assert r1.metadata == r2.metadata
            assert r1.fatigue_score == r2.fatigue_score == None


# =====================================================================
# 7. Immutability
# =====================================================================

def test_immutability_of_inputs_and_structures(base_time):
    """Verify pipeline execution does not mutate inputs, context, baseline, or configuration."""
    baseline = make_baseline()
    context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)
    sample = make_sample(base_time, hr=72.0)

    # Capture initial values
    initial_sample_hr = sample.heart_rate
    initial_ctx_g = context.external_g_load
    initial_base_hr = baseline.resting_heart_rate

    pipeline = AeroVitalPipeline(baseline=baseline)
    _ = pipeline.process_sample(sample, context=context)

    assert sample.heart_rate == initial_sample_hr
    assert context.external_g_load == initial_ctx_g
    assert baseline.resting_heart_rate == initial_base_hr


# =====================================================================
# 8. Provenance
# =====================================================================

def test_provenance_and_metadata_retention(base_time):
    """Verify final results preserve estimator metadata, baseline version, and disclaimer."""
    baseline = make_baseline(version="PROVENANCE-2026-X")
    pipeline = AeroVitalPipeline(baseline=baseline)
    context = OperationalContext(timestamp=base_time, external_g_load=1.0, mission_phase=MissionPhase.CRUISE)

    samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(8)]
    results = pipeline.process_sequence(samples, context=context)

    assert len(results) > 0
    res = results[-1]
    assert res.metadata.baseline_version_used == "PROVENANCE-2026-X"
    assert "AeroVitalConfidenceEvaluator" in res.metadata.estimator_id
    assert "provisional prototype" in res.metadata.disclaimer.lower()
    assert res.metadata.is_provisional is True
    assert 0.0 <= res.confidence <= 1.0


# =====================================================================
# 9. Architectural Boundary Audit (AST / Source Code Inspection)
# =====================================================================

class TestArchitecturalBoundaries:
    """Programmatic audit verifying strict separation of concerns across the core."""

    def test_pipeline_contains_no_physiological_or_confidence_logic(self):
        """pipeline.py must contain no physiological thresholds, confidence weights, or SQI formulas."""
        pipeline_code = (Path(__file__).parent.parent / "pipeline" / "pipeline.py").read_text()

        forbidden_tokens = [
            "hr_deviation_workload_threshold",
            "rmssd_ratio_fatigue_threshold",
            "g_load_workload_threshold",
            "weight_global_sqi",
            "weight_channel_quality",
            "compute_breakdown",
            "unacceptable_telemetry_cap",
        ]
        for token in forbidden_tokens:
            assert token not in pipeline_code, f"Forbidden business logic token '{token}' in pipeline.py"

    def test_step8_contains_no_new_state_rules(self):
        """Step 8 evaluator.py must not make new state determinations."""
        step8_code = (Path(__file__).parent.parent / "confidence" / "evaluator.py").read_text()
        forbidden_tokens = [
            "hr_deviation_from_baseline",
            "hrv_rmssd_ratio_to_baseline",
            "FatigueState.FATIGUE ==",  # must not assign or infer fatigue state directly
        ]
        for token in forbidden_tokens:
            assert token not in step8_code, f"Forbidden state determination logic '{token}' in Step 8"

    def test_step7_contains_no_confidence_calculations(self):
        """Step 7 rules.py must not calculate confidence or global SQI weights."""
        step7_code = (Path(__file__).parent.parent / "intelligence" / "rules.py").read_text()
        forbidden_tokens = [
            "confidence =",
            "overall_confidence",
            "weight_global_sqi",
        ]
        for token in forbidden_tokens:
            assert token not in step7_code, f"Forbidden confidence logic '{token}' in Step 7"

    def test_core_engine_has_no_framework_or_network_dependencies(self):
        """Core engine must be framework-independent: no Django, FastAPI, DB, or network access."""
        core_dir = Path(__file__).parent.parent
        all_py_files = [f for f in core_dir.rglob("*.py") if "__pycache__" not in str(f)]

        forbidden_imports = [
            "django",
            "fastapi",
            "sqlalchemy",
            "psycopg",
            "requests",
            "httpx",
            "aiohttp",
            "websockets",
            "wear_os",
        ]

        for py_file in all_py_files:
            text = py_file.read_text().lower()
            for imp in forbidden_imports:
                assert f"import {imp}" not in text and f"from {imp}" not in text, (
                    f"Forbidden framework import '{imp}' discovered in {py_file.name}"
                )
