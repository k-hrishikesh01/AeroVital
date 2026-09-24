"""Tests for AeroVital Core Signal and Context Validation.

Verifies:
- Physiological plausibility (HR, RR intervals, SpO2, skin temperature, battery).
- Required vs. optional field handling (graceful handling of partial sensor sets).
- Timestamp validity and monotonicity (strict and non-strict).
- Rejection of invalid numeric values (NaN, +Inf, -Inf).
- RR interval plausibility (both single values and lists).
- Sensor consistency (3-axis accelerometer complete triplet check).
- Operational flight context validation.
"""

from datetime import datetime, timedelta, timezone
import pytest

from backend.core.schemas.telemetry import TelemetrySample
from backend.core.schemas.context import OperationalContext, MissionPhase
from backend.core.validation import (
    TelemetryValidator,
    ValidationConfig,
    SignalValidationError,
    PhysiologicalPlausibilityError,
    TimestampMonotonicityError,
    NumericValueError,
    SensorConsistencyError,
)


@pytest.fixture
def validator():
    return TelemetryValidator()


@pytest.fixture
def base_time():
    return datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


class TestPhysiologicalPlausibility:
    def test_valid_physiological_sample_passes(self, validator, base_time):
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=72.0,
            rr_interval=[820.0, 840.0],
            spo2=98.0,
            skin_temperature=36.2,
            battery_level=80.0,
            steps=1500,
            accel_x=0.01,
            accel_y=0.98,
            accel_z=0.12,
        )
        validated = validator.validate_sample(sample)
        assert validated == sample

    @pytest.mark.parametrize("hr", [29.9, 10.0, 0.0, -5.0, 240.1, 300.0])
    def test_invalid_heart_rate_fails(self, validator, base_time, hr):
        sample = TelemetrySample(timestamp=base_time, heart_rate=hr)
        with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "heart_rate"

    @pytest.mark.parametrize("hr", [30.0, 60.0, 120.0, 180.0, 240.0])
    def test_boundary_heart_rate_passes(self, validator, base_time, hr):
        sample = TelemetrySample(timestamp=base_time, heart_rate=hr)
        validated = validator.validate_sample(sample)
        assert validated.heart_rate == hr

    @pytest.mark.parametrize("rr", [249.0, 100.0, 0.0, -50.0, 2501.0, 4000.0])
    def test_invalid_single_rr_interval_fails(self, validator, base_time, rr):
        sample = TelemetrySample(timestamp=base_time, rr_interval=rr)
        with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "rr_interval"

    def test_invalid_rr_in_list_fails(self, validator, base_time):
        # Even if first two are valid, third is biologically impossible
        sample = TelemetrySample(timestamp=base_time, rr_interval=[800.0, 850.0, 150.0])
        with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "rr_interval"

    @pytest.mark.parametrize("spo2", [49.9, 0.0, -10.0, 100.1, 110.0])
    def test_invalid_spo2_fails(self, validator, base_time, spo2):
        sample = TelemetrySample(timestamp=base_time, spo2=spo2)
        with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "spo2"

    @pytest.mark.parametrize("temp", [19.9, 5.0, -2.0, 45.1, 55.0])
    def test_invalid_skin_temperature_fails(self, validator, base_time, temp):
        sample = TelemetrySample(timestamp=base_time, skin_temperature=temp)
        with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "skin_temperature"

    @pytest.mark.parametrize("battery", [-1.0, 100.1, 150.0])
    def test_invalid_battery_fails(self, validator, base_time, battery):
        sample = TelemetrySample(timestamp=base_time, battery_level=battery)
        with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "battery_level"

    def test_negative_steps_fails(self, validator, base_time):
        sample = TelemetrySample(timestamp=base_time, steps=-10)
        with pytest.raises(NumericValueError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "steps"


class TestRequiredAndOptionalFields:
    def test_minimal_sample_with_only_timestamp_passes(self, validator, base_time):
        sample = TelemetrySample(timestamp=base_time)
        validated = validator.validate_sample(sample)
        assert validated.timestamp == base_time
        assert validated.heart_rate is None
        assert validated.spo2 is None

    def test_partial_sensor_set_passes(self, validator, base_time):
        # E.g. device only measures heart rate and steps
        sample = TelemetrySample(
            timestamp=base_time,
            heart_rate=65.0,
            steps=350,
        )
        validated = validator.validate_sample(sample)
        assert validated.heart_rate == 65.0
        assert validated.steps == 350
        assert validated.rr_interval is None
        assert validated.accel_x is None


class TestNumericValues:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("heart_rate", float("nan")),
            ("heart_rate", float("inf")),
            ("heart_rate", float("-inf")),
            ("spo2", float("nan")),
            ("skin_temperature", float("inf")),
            ("battery_level", float("nan")),
            ("accel_x", float("nan")),
        ],
    )
    def test_nan_or_inf_in_scalars_fails(self, validator, base_time, field, value):
        kwargs = {"timestamp": base_time, field: value}
        # If accel_x, provide y and z so consistency passes and nan fails
        if field == "accel_x":
            kwargs["accel_y"] = 0.0
            kwargs["accel_z"] = 1.0
        sample = TelemetrySample(**kwargs)
        with pytest.raises(NumericValueError):
            validator.validate_sample(sample)

    def test_nan_in_rr_interval_list_fails(self, validator, base_time):
        sample = TelemetrySample(timestamp=base_time, rr_interval=[800.0, float("nan")])
        with pytest.raises(NumericValueError):
            validator.validate_sample(sample)


class TestTimestampMonotonicity:
    def test_strictly_increasing_timestamps_pass(self, validator, base_time):
        s1 = TelemetrySample(timestamp=base_time, heart_rate=70.0)
        s2 = TelemetrySample(timestamp=base_time + timedelta(seconds=1), heart_rate=71.0)
        validator.validate_sample(s1)
        validator.validate_sample(s2, previous_timestamp=s1.timestamp)

    def test_retrograde_timestamp_fails(self, validator, base_time):
        s1 = TelemetrySample(timestamp=base_time, heart_rate=70.0)
        s2 = TelemetrySample(timestamp=base_time - timedelta(seconds=1), heart_rate=71.0)
        with pytest.raises(TimestampMonotonicityError):
            validator.validate_sample(s2, previous_timestamp=s1.timestamp)

    def test_duplicate_timestamp_fails_in_strict_mode(self, validator, base_time):
        s1 = TelemetrySample(timestamp=base_time, heart_rate=70.0)
        s2 = TelemetrySample(timestamp=base_time, heart_rate=71.0)
        with pytest.raises(TimestampMonotonicityError):
            validator.validate_sample(s2, previous_timestamp=s1.timestamp)

    def test_duplicate_timestamp_passes_in_non_strict_mode(self, base_time):
        non_strict_validator = TelemetryValidator(
            config=ValidationConfig(strict_monotonicity=False)
        )
        s1 = TelemetrySample(timestamp=base_time, heart_rate=70.0)
        s2 = TelemetrySample(timestamp=base_time, heart_rate=71.0)
        non_strict_validator.validate_sample(s1)
        validated_s2 = non_strict_validator.validate_sample(s2, previous_timestamp=s1.timestamp)
        assert validated_s2.timestamp == s1.timestamp

    def test_timezone_aware_vs_naive_fails(self, validator, base_time):
        naive_time = datetime(2026, 9, 22, 12, 0, 1)
        sample = TelemetrySample(timestamp=naive_time, heart_rate=70.0)
        with pytest.raises(TimestampMonotonicityError):
            validator.validate_sample(sample, previous_timestamp=base_time)


class TestAccelerometerValidation:
    def test_all_axes_none_passes(self, validator, base_time):
        sample = TelemetrySample(timestamp=base_time, accel_x=None, accel_y=None, accel_z=None)
        validated = validator.validate_sample(sample)
        assert not validated.has_acceleration()

    def test_complete_triplet_passes(self, validator, base_time):
        sample = TelemetrySample(
            timestamp=base_time,
            accel_x=0.05,
            accel_y=0.98,
            accel_z=-0.12,
        )
        validated = validator.validate_sample(sample)
        assert validated.has_acceleration()

    @pytest.mark.parametrize(
        "x,y,z",
        [
            (0.1, None, None),
            (None, 0.2, None),
            (None, None, 0.3),
            (0.1, 0.2, None),
            (0.1, None, 0.3),
            (None, 0.2, 0.3),
        ],
    )
    def test_incomplete_accelerometer_triplet_fails(self, validator, base_time, x, y, z):
        sample = TelemetrySample(timestamp=base_time, accel_x=x, accel_y=y, accel_z=z)
        with pytest.raises(SensorConsistencyError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "accelerometer"

    def test_extreme_accelerometer_axis_fails(self, validator, base_time):
        sample = TelemetrySample(
            timestamp=base_time,
            accel_x=300.0,  # exceeds default limit of 250.0
            accel_y=0.0,
            accel_z=1.0,
        )
        with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
            validator.validate_sample(sample)
        assert exc_info.value.field == "accel_x"


class TestOperationalContextValidation:
    def test_valid_context_passes(self, validator, base_time):
        ctx = OperationalContext(
            timestamp=base_time,
            mission_phase=MissionPhase.CRUISE,
            external_g_load=1.05,
            flight_duration_sec=1200.0,
            altitude_feet=24000.0,
        )
        validated = validator.validate_context(ctx)
        assert validated == ctx

    @pytest.mark.parametrize("g_load", [-11.0, 25.0])
    def test_extreme_g_load_fails(self, validator, base_time, g_load):
        ctx = OperationalContext(timestamp=base_time, external_g_load=g_load)
        with pytest.raises(PhysiologicalPlausibilityError) as exc_info:
            validator.validate_context(ctx)
        assert exc_info.value.field == "external_g_load"

    def test_negative_flight_duration_fails(self, validator, base_time):
        ctx = OperationalContext(timestamp=base_time, flight_duration_sec=-5.0)
        with pytest.raises(NumericValueError) as exc_info:
            validator.validate_context(ctx)
        assert exc_info.value.field == "flight_duration_sec"

    def test_context_retrograde_timestamp_fails(self, validator, base_time):
        c1 = OperationalContext(timestamp=base_time)
        c2 = OperationalContext(timestamp=base_time - timedelta(seconds=1))
        with pytest.raises(TimestampMonotonicityError):
            validator.validate_context(c2, previous_timestamp=c1.timestamp)
