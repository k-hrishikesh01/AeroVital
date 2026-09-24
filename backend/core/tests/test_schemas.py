"""Tests for AeroVital Core Schemas.

Validates:
- Preserved backend contract fields on TelemetrySample.
- Optional channel behavior (engine works with whatever subset is provided).
- PilotBaseline pilot-specific versioned schema without population defaults.
- OperationalContext decoupling.
- QualityAssessment and ChannelQuality bounds.
- FeatureVector defaults and baseline representation.
- FatigueEstimationResult structure, independent confidence, and provisional metadata.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from backend.core.schemas import (
    TelemetrySample,
    MissionPhase,
    OperationalContext,
    PilotBaseline,
    ChannelQuality,
    QualityAssessment,
    HeartRateFeatures,
    HRVFeatures,
    MotionFeatures,
    BaselineComparisonFeatures,
    FeatureVector,
    FatigueState,
    EstimationMetadata,
    FatigueEstimationResult,
)


class TestTelemetrySampleSchema:
    def test_minimal_telemetry_sample(self):
        now = datetime.now(timezone.utc)
        sample = TelemetrySample(timestamp=now)

        assert sample.timestamp == now
        assert sample.heart_rate is None
        assert sample.rr_interval is None
        assert sample.spo2 is None
        assert sample.skin_temperature is None
        assert sample.activity_level is None
        assert sample.steps is None
        assert sample.accel_x is None
        assert sample.accel_y is None
        assert sample.accel_z is None
        assert sample.battery_level is None
        assert sample.raw_payload is None
        assert sample.get_rr_intervals() == []
        assert not sample.has_acceleration()

    def test_full_preserved_contract(self):
        now = datetime.now(timezone.utc)
        sample = TelemetrySample(
            timestamp=now,
            heart_rate=72.5,
            rr_interval=[820.0, 835.5],
            spo2=98.0,
            skin_temperature=36.4,
            activity_level="SEDENTARY",
            steps=1420,
            accel_x=0.02,
            accel_y=0.98,
            accel_z=0.15,
            battery_level=85.0,
            raw_payload={"sensor_model": "samsung_bioactive_v1", "snr": 18.2},
        )

        assert sample.heart_rate == 72.5
        assert sample.get_rr_intervals() == [820.0, 835.5]
        assert sample.spo2 == 98.0
        assert sample.skin_temperature == 36.4
        assert sample.steps == 1420
        assert sample.battery_level == 85.0
        assert sample.has_acceleration()
        assert sample.raw_payload["sensor_model"] == "samsung_bioactive_v1"

    def test_single_rr_interval_normalization(self):
        now = datetime.now(timezone.utc)
        sample = TelemetrySample(timestamp=now, rr_interval=850.0)
        assert sample.get_rr_intervals() == [850.0]

    def test_immutability(self):
        now = datetime.now(timezone.utc)
        sample = TelemetrySample(timestamp=now, heart_rate=70.0)
        with pytest.raises(ValidationError):
            sample.heart_rate = 80.0  # type: ignore

    def test_serialization_round_trip(self):
        now = datetime.now(timezone.utc)
        original = TelemetrySample(
            timestamp=now,
            heart_rate=68.0,
            rr_interval=[880.0],
            accel_x=0.1,
            accel_y=0.2,
            accel_z=0.98,
        )
        data = original.model_dump(mode="json")
        reconstructed = TelemetrySample.model_validate(data)

        assert reconstructed.timestamp == original.timestamp
        assert reconstructed.heart_rate == original.heart_rate
        assert reconstructed.get_rr_intervals() == [880.0]
        assert reconstructed.accel_z == 0.98


class TestOperationalContextSchema:
    def test_operational_context_defaults(self):
        now = datetime.now(timezone.utc)
        ctx = OperationalContext(timestamp=now)

        assert ctx.timestamp == now
        assert ctx.mission_phase is None
        assert ctx.external_g_load is None
        assert ctx.flight_duration_sec is None
        assert ctx.metadata == {}

    def test_operational_context_full(self):
        now = datetime.now(timezone.utc)
        ctx = OperationalContext(
            timestamp=now,
            mission_phase=MissionPhase.HIGH_G,
            external_g_load=4.5,
            flight_duration_sec=3600.0,
            altitude_feet=18000.0,
            cabin_pressure_altitude_feet=6000.0,
            metadata={"callsign": "VIPER-01", "sortie_type": "TACTICAL"},
        )

        assert ctx.mission_phase == MissionPhase.HIGH_G
        assert ctx.external_g_load == 4.5
        assert ctx.altitude_feet == 18000.0
        assert ctx.metadata["callsign"] == "VIPER-01"


class TestPilotBaselineSchema:
    def test_pilot_baseline_creation(self):
        now = datetime.now(timezone.utc)
        baseline = PilotBaseline(
            pilot_id="PILOT-402",
            baseline_version="2026-Q1-v1.0",
            created_at=now,
            resting_heart_rate=58.0,
            baseline_rmssd=48.5,
            baseline_sdnn=62.0,
            baseline_mean_rr=1034.0,
            calibration_duration_sec=300.0,
        )

        assert baseline.pilot_id == "PILOT-402"
        assert baseline.baseline_version == "2026-Q1-v1.0"
        assert baseline.resting_heart_rate == 58.0
        assert baseline.baseline_rmssd == 48.5
        assert baseline.is_calibrated is True

    def test_missing_required_fields_fails(self):
        # resting_heart_rate, pilot_id, baseline_version, created_at are required
        with pytest.raises(ValidationError):
            PilotBaseline(pilot_id="PILOT-001")  # type: ignore


class TestQualityAssessmentSchema:
    def test_quality_assessment_structure(self):
        now = datetime.now(timezone.utc)
        hr_quality = ChannelQuality(
            channel_name="heart_rate",
            sqi_score=0.92,
            is_usable=True,
            missing_sample_ratio=0.05,
            motion_artifact_detected=False,
        )
        assessment = QualityAssessment(
            timestamp=now,
            overall_sqi=0.90,
            channels={"heart_rate": hr_quality},
            motion_corruption_index=0.1,
            is_telemetry_acceptable=True,
        )

        assert assessment.overall_sqi == 0.90
        assert assessment.get_channel_sqi("heart_rate") == 0.92
        assert assessment.get_channel_sqi("nonexistent") is None
        assert assessment.is_telemetry_acceptable is True

    def test_sqi_out_of_bounds_fails(self):
        with pytest.raises(ValidationError):
            ChannelQuality(
                channel_name="hr",
                sqi_score=1.5,  # must be <= 1.0
                is_usable=True,
            )


class TestFeaturesSchema:
    def test_feature_vector_defaults(self):
        now = datetime.now(timezone.utc)
        fv = FeatureVector(
            window_start=now,
            window_end=now,
            window_duration_sec=60.0,
        )

        assert fv.window_duration_sec == 60.0
        assert fv.hr_features.mean_hr is None
        assert fv.hrv_features.rmssd_ms is None
        assert fv.motion_features.activity_intensity is None
        # Must explicitly default to baseline unavailable and None deviations
        assert fv.baseline_features.baseline_available is False
        assert fv.baseline_features.hr_deviation_from_baseline is None
        assert fv.baseline_features.hrv_rmssd_ratio_to_baseline is None

    def test_populated_feature_vector(self):
        now = datetime.now(timezone.utc)
        fv = FeatureVector(
            window_start=now,
            window_end=now,
            window_duration_sec=120.0,
            hr_features=HeartRateFeatures(mean_hr=82.0, min_hr=75.0, max_hr=90.0, hr_std=4.2),
            hrv_features=HRVFeatures(mean_rr_ms=731.0, rmssd_ms=32.0, valid_intervals_count=110),
            motion_features=MotionFeatures(mean_magnitude=1.02, activity_intensity=0.15),
            baseline_features=BaselineComparisonFeatures(
                baseline_available=True,
                hr_deviation_from_baseline=14.0,
                hrv_rmssd_ratio_to_baseline=0.75,
            ),
        )

        assert fv.hr_features.mean_hr == 82.0
        assert fv.hrv_features.rmssd_ms == 32.0
        assert fv.baseline_features.baseline_available is True
        assert fv.baseline_features.hr_deviation_from_baseline == 14.0


class TestFatigueResultSchema:
    def test_provisional_result_normal_state(self):
        now = datetime.now(timezone.utc)
        metadata = EstimationMetadata(
            estimator_id="ProvisionalRuleBasedEstimator",
            is_provisional=True,
            confidence_threshold_used=0.40,
            baseline_version_used="2026-v1.0",
        )
        result = FatigueEstimationResult(
            timestamp=now,
            fatigue_score=0.22,
            fatigue_state=FatigueState.NORMAL,
            confidence=0.85,
            dominant_factors=["Baseline resting rate maintained"],
            overall_sqi=0.95,
            metadata=metadata,
        )

        assert result.fatigue_state == FatigueState.NORMAL
        assert result.fatigue_score == 0.22
        assert result.confidence == 0.85
        assert result.metadata.is_provisional is True
        assert "not clinically" in result.metadata.disclaimer

    def test_insufficient_data_result(self):
        now = datetime.now(timezone.utc)
        metadata = EstimationMetadata(
            estimator_id="ProvisionalRuleBasedEstimator",
            is_provisional=True,
            confidence_threshold_used=0.40,
            baseline_version_used=None,
        )
        # Fatigue score can be None when abstaining
        result = FatigueEstimationResult(
            timestamp=now,
            fatigue_score=None,
            fatigue_state=FatigueState.INSUFFICIENT_DATA,
            confidence=0.20,
            dominant_factors=["Missing pilot baseline", "Immature temporal window"],
            overall_sqi=0.50,
            metadata=metadata,
        )

        assert result.fatigue_state == FatigueState.INSUFFICIENT_DATA
        assert result.fatigue_score is None
        assert result.confidence < 0.40
