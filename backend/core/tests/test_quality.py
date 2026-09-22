"""Tests for AeroVital Core Signal Quality Assessment.

Verifies:
- Good-quality clean signals achieve high SQI scores.
- Missing optional channels are marked as UNAVAILABLE without receiving synthetic quality.
- Missing optional channels do not drag down overall SQI of available channels.
- Timestamp continuity and sampling interval jitter degrade timing quality.
- Accelerometer dynamic motion degrades optical PPG signals (HR, RR) without being treated as fatigue.
- Insufficient history is explicitly detected and distinguished from poor quality.
- Per-channel SQI metrics and notes are informative.
- Overall SQI aggregation is strictly within [0.0, 1.0].
- No synthetic or imputed physiological values are generated anywhere in the quality layer.
- Complete independence from fatigue scoring, fatigue states, or medical logic.
"""

from datetime import datetime, timedelta, timezone
import pytest

from backend.core.schemas.telemetry import TelemetrySample
from backend.core.schemas.quality import QualityAssessment, ChannelQuality
from backend.core.quality import (
    AccelUnit,
    SignalQualityAssessor,
    QualityConfig,
    evaluate_motion_corruption,
    evaluate_sampling_continuity,
    compute_dynamic_acceleration,
)


@pytest.fixture
def assessor():
    return SignalQualityAssessor()


@pytest.fixture
def assessor_g():
    return SignalQualityAssessor(config=QualityConfig(accel_unit=AccelUnit.G))


@pytest.fixture
def base_time():
    return datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


class TestGoodQualitySignal:
    def test_pristine_single_sample(self, assessor, base_time):
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=72.0,
            rr_interval=[820.0, 835.0],
            accel_x=0.01,
            accel_y=0.98,
            accel_z=0.10,  # magnitude ~ 0.985 (still / gravity only)
        )
        qa = assessor.assess_sample(sample)

        assert qa.overall_sqi >= 0.90
        assert qa.is_telemetry_acceptable is True
        assert qa.motion_corruption_index < 0.10
        assert qa.channels["heart_rate"].is_usable is True
        assert qa.channels["heart_rate"].sqi_score >= 0.90
        assert qa.channels["rr_interval"].is_usable is True
        assert qa.channels["accelerometer"].is_usable is True

    def test_pristine_window(self, assessor, base_time):
        samples = [
            TelemetrySample(
                timestamp=base_time + timedelta(seconds=i),
                heart_rate=70.0 + (i % 3),
                rr_interval=[850.0],
                accel_x=0.0,
                accel_y=1.0,
                accel_z=0.0,
            )
            for i in range(10)
        ]
        qa = assessor.assess_window(samples)

        assert qa.overall_sqi >= 0.95
        assert qa.is_telemetry_acceptable is True
        assert qa.motion_corruption_index == 0.0
        assert qa.channels["heart_rate"].is_usable is True
        assert qa.channels["rr_interval"].is_usable is True


class TestMissingOptionalChannels:
    def test_missing_spo2_and_temp_does_not_invalidate_sample(self, assessor, base_time):
        # Realistic Wear OS sample: only HR, RR, Accel. SpO2 and Temp are None.
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=75.0,
            rr_interval=800.0,
            accel_x=0.0,
            accel_y=1.0,
            accel_z=0.0,
        )
        qa = assessor.assess_sample(sample)

        assert qa.is_telemetry_acceptable is True
        assert qa.overall_sqi >= 0.90
        # Optional channels marked as UNAVAILABLE, not receiving synthetic quality
        assert qa.channels["spo2"].sqi_score == 0.0
        assert qa.channels["spo2"].is_usable is False
        assert "UNAVAILABLE" in (qa.channels["spo2"].notes or "")
        assert qa.channels["skin_temperature"].sqi_score == 0.0
        assert qa.channels["skin_temperature"].is_usable is False
        assert "UNAVAILABLE" in (qa.channels["skin_temperature"].notes or "")

    def test_all_physiological_channels_missing_fails_acceptability(self, assessor, base_time):
        # Sample with only accelerometer and battery; no HR or RR
        sample = TelemetrySample(
            timestamp=base_time,
            accel_x=0.0,
            accel_y=1.0,
            accel_z=0.0,
            battery_level=90.0,
        )
        qa = assessor.assess_sample(sample)

        assert qa.is_telemetry_acceptable is False
        assert qa.channels["heart_rate"].is_usable is False
        assert qa.channels["rr_interval"].is_usable is False


class TestMotionCorruptedSignal:
    def test_high_motion_degrades_optical_channels(self, assessor_g, base_time):
        # Strong dynamic acceleration (e.g. wrist shaking: 2.5g dynamic acceleration)
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=88.0,
            rr_interval=[680.0],
            accel_x=1.8,
            accel_y=1.5,
            accel_z=0.9,  # magnitude = sqrt(3.24 + 2.25 + 0.81) = sqrt(6.30) ~ 2.51g -> dynamic ~ 1.51g
        )
        qa = assessor_g.assess_sample(sample)

        assert qa.motion_corruption_index > 0.80
        assert qa.channels["heart_rate"].motion_artifact_detected is True
        assert qa.channels["rr_interval"].motion_artifact_detected is True
        # Optical SQIs must be degraded compared to pristine
        assert qa.channels["heart_rate"].sqi_score < 0.70
        assert qa.channels["rr_interval"].sqi_score < 0.50
        # Notice: accelerometer data itself is present and clean, so accel SQI is not penalized by motion
        assert qa.channels["accelerometer"].sqi_score == 1.0

    def test_window_motion_variance(self, assessor_g, base_time):
        # Rapidly varying accelerometer readings across window
        samples = []
        for i in range(10):
            sign = 1 if i % 2 == 0 else -1
            samples.append(
                TelemetrySample(
                    timestamp=base_time + timedelta(seconds=i),
                    heart_rate=95.0,
                    rr_interval=[630.0],
                    accel_x=sign * 1.5,
                    accel_y=1.0 + sign * 0.8,
                    accel_z=sign * 1.2,
                )
            )
        qa = assessor_g.assess_window(samples)

        assert qa.motion_corruption_index > 0.50
        assert qa.channels["heart_rate"].motion_artifact_detected is True
        assert "Motion artifact detected" in (qa.channels["heart_rate"].notes or "")


class TestSamplingContinuityAndJitter:
    def test_sample_timing_gap_penalizes_sqi(self, assessor, base_time):
        s1 = TelemetrySample(timestamp=base_time, heart_rate=70.0)
        # Expected interval is 1.0s; 5.0s gap indicates dropped frames
        s2 = TelemetrySample(timestamp=base_time + timedelta(seconds=5), heart_rate=71.0)

        qa = assessor.assess_sample(s2, previous_timestamp=s1.timestamp)
        assert qa.channels["heart_rate"].missing_sample_ratio > 0.50
        assert qa.channels["heart_rate"].sqi_score < 0.60

    def test_window_jitter_detection(self, assessor, base_time):
        # Irregular timestamps: 0s, 0.2s, 2.5s, 2.7s, 6.0s (high jitter & missing samples)
        irregular_seconds = [0.0, 0.2, 2.5, 2.7, 6.0, 6.1, 7.5, 9.8]
        samples = [
            TelemetrySample(
                timestamp=base_time + timedelta(seconds=sec),
                heart_rate=75.0,
            )
            for sec in irregular_seconds
        ]
        qa = assessor.assess_window(samples)

        assert qa.channels["heart_rate"].missing_sample_ratio > 0.0
        assert qa.channels["heart_rate"].sqi_score < 0.80


class TestInsufficientHistory:
    def test_window_with_insufficient_samples_flagged(self, assessor, base_time):
        # Config requires minimum 5 samples; provide only 2
        samples = [
            TelemetrySample(timestamp=base_time, heart_rate=72.0),
            TelemetrySample(timestamp=base_time + timedelta(seconds=1), heart_rate=73.0),
        ]
        qa = assessor.assess_window(samples)

        assert "INSUFFICIENT_HISTORY" in (qa.channels["heart_rate"].notes or "")
        assert qa.channels["heart_rate"].is_usable is False
        assert qa.channels["heart_rate"].sqi_score < 0.40


class TestNoDataImputation:
    def test_quality_layer_never_fabricates_or_alters_telemetry(self, assessor, base_time):
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=80.0,
            # RR, SpO2, Temp, Accel all omitted
        )
        qa = assessor.assess_sample(sample)

        # Original sample is immutable and unmodified
        assert sample.rr_interval is None
        assert sample.spo2 is None
        assert sample.skin_temperature is None
        # Quality assessment reflects what exists without synthesizing dummy data
        assert qa.channels["rr_interval"].sqi_score == 0.0
        assert qa.channels["spo2"].sqi_score == 0.0


class TestQualityBoundsAndIndependence:
    def test_all_sqi_scores_strictly_bounded(self, assessor, base_time):
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=70.0,
            rr_interval=[800.0],
            accel_x=0.0,
            accel_y=1.0,
            accel_z=0.0,
        )
        qa = assessor.assess_sample(sample)

        assert 0.0 <= qa.overall_sqi <= 1.0
        assert 0.0 <= qa.motion_corruption_index <= 1.0
        for ch_name, ch in qa.channels.items():
            assert 0.0 <= ch.sqi_score <= 1.0
            assert 0.0 <= ch.missing_sample_ratio <= 1.0

    def test_quality_layer_has_no_fatigue_logic(self, assessor, base_time):
        # Verify QualityAssessment object has no fatigue scores, states, or fatigue fields
        sample = TelemetrySample(timestamp=base_time, heart_rate=160.0)  # Elevated HR
        qa = assessor.assess_sample(sample)

        # Quality evaluates signal integrity (present, no motion), NOT fatigue
        assert not hasattr(qa, "fatigue_score")
        assert not hasattr(qa, "fatigue_state")
        assert qa.channels["heart_rate"].is_usable is True
        # A physiologically high HR has high signal quality if received cleanly
        assert qa.channels["heart_rate"].sqi_score >= 0.90


class TestExplicitAccelerometerUnitContract:
    def test_default_config_unit_is_unspecified(self):
        # The AeroVital core must never silently assume the native unit of an accelerometer stream
        assert QualityConfig().accel_unit == AccelUnit.UNSPECIFIED

    def test_1g_interpreted_correctly_when_unit_g(self, base_time):
        config = QualityConfig(accel_unit="g")
        assessor = SignalQualityAssessor(config=config)
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=70.0,
            accel_x=0.0,
            accel_y=1.0,
            accel_z=0.0,
        )
        qa = assessor.assess_sample(sample)
        assert qa.motion_corruption_index == 0.0
        assert qa.channels["heart_rate"].motion_artifact_detected is False

    def test_981_interpreted_correctly_when_unit_ms2(self, base_time):
        config = QualityConfig(accel_unit="m/s2")
        assessor = SignalQualityAssessor(config=config)
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=70.0,
            accel_x=0.0,
            accel_y=9.80665,
            accel_z=0.0,
        )
        qa = assessor.assess_sample(sample)
        assert qa.motion_corruption_index == 0.0
        assert qa.channels["heart_rate"].motion_artifact_detected is False

    def test_5g_remains_5g_and_not_ms2(self, base_time):
        # With explicit unit="g", 5g has dynamic acceleration |5.0 - 1.0| = 4.0g.
        # It must NOT be guessed as ~5 m/s² (which would erroneously result in |5.0 - 9.81|).
        config = QualityConfig(accel_unit="g")
        assessor = SignalQualityAssessor(config=config)
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=70.0,
            accel_x=0.0,
            accel_y=5.0,
            accel_z=0.0,
        )
        qa = assessor.assess_sample(sample)
        # 4.0g dynamic acceleration easily saturates motion_corruption_index to 1.0
        assert qa.motion_corruption_index == 1.0
        assert qa.channels["heart_rate"].motion_artifact_detected is True
        # Direct verification of dynamic acceleration function
        dyn = compute_dynamic_acceleration(0.0, 5.0, 0.0, unit="g")
        assert dyn == 4.0

    def test_unspecified_units_do_not_trigger_automatic_guessing(self, base_time):
        config = QualityConfig(accel_unit="unspecified")
        assessor = SignalQualityAssessor(config=config)
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=70.0,
            accel_x=0.0,
            accel_y=5.0,
            accel_z=0.0,
        )
        qa = assessor.assess_sample(sample)
        # Motion corruption is NOT evaluated; no guessing is performed
        assert qa.motion_corruption_index == 0.0
        assert qa.channels["heart_rate"].motion_artifact_detected is False
        assert "Unit unspecified" in (qa.channels["accelerometer"].notes or "")
        # Direct function returns None
        assert compute_dynamic_acceleration(0.0, 5.0, 0.0, unit="unspecified") is None


class TestCentralizedQualityParameters:
    def test_configurable_single_sample_motion_penalty(self, base_time):
        # Test custom motion penalty coefficient
        config = QualityConfig(
            accel_unit="g",
            single_sample_motion_penalty_hr=0.10,  # lower penalty than default 0.45
        )
        assessor = SignalQualityAssessor(config=config)
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=70.0,
            accel_x=1.0,
            accel_y=1.0,
            accel_z=1.0,  # magnitude = sqrt(3) ~ 1.732g -> dynamic ~ 0.732g
        )
        qa = assessor.assess_sample(sample)
        # With penalty coefficient 0.10, HR SQI remains high (> 0.90)
        assert qa.channels["heart_rate"].sqi_score >= 0.90

    def test_configurable_insufficient_history_penalty_cap(self, base_time):
        config = QualityConfig(
            min_history_samples=5,
            insufficient_history_penalty_cap=0.20,  # lower cap than default 0.40
        )
        assessor = SignalQualityAssessor(config=config)
        samples = [
            TelemetrySample(timestamp=base_time, heart_rate=70.0),
            TelemetrySample(timestamp=base_time + timedelta(seconds=1), heart_rate=71.0),
        ]
        qa = assessor.assess_window(samples)
        assert qa.channels["heart_rate"].sqi_score <= 0.20
