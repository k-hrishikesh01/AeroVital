"""Signal and Context Validation Layer for AeroVital Core.

Implements strict validation covering:
- Physiological plausibility (HR, RR intervals, SpO2, skin temperature).
- Required vs. optional field handling (optional fields are preserved as None).
- Timestamp validity and monotonicity tracking.
- Non-finite numeric validation (NaN, +Inf, -Inf detection).
- Sensor consistency (3-axis accelerometer integrity).
"""

from datetime import datetime, timezone
import math
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.core.schemas.telemetry import TelemetrySample
from backend.core.schemas.context import OperationalContext
from backend.core.validation.exceptions import (
    PhysiologicalPlausibilityError,
    TimestampMonotonicityError,
    NumericValueError,
    SensorConsistencyError,
)


class ValidationConfig(BaseModel):
    """Configurable engineering input-sanity bounds and rules for signal validation.
    
    IMPORTANT: The default numerical boundaries below represent prototype engineering
    sanity limits for catching obvious sensor malfunctions or invalid data packets.
    They are NOT medical thresholds, fatigue thresholds, aviation certification limits,
    or clinically validated physiological cutoffs.
    """
    model_config = ConfigDict(frozen=True)

    # Configurable engineering input-sanity bounds (Prototype defaults)
    hr_min: float = Field(
        default=30.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    hr_max: float = Field(
        default=240.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    
    rr_min_ms: float = Field(
        default=250.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    rr_max_ms: float = Field(
        default=2500.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    
    spo2_min: float = Field(
        default=50.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    spo2_max: float = Field(
        default=100.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    
    temp_min_c: float = Field(
        default=20.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    temp_max_c: float = Field(
        default=45.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    
    accel_axis_abs_max: float = Field(
        default=250.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    
    g_load_min: float = Field(
        default=-10.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )
    g_load_max: float = Field(
        default=20.0,
        description="Configurable engineering input-sanity bound for the current prototype. This is not a medical threshold, fatigue threshold, aviation certification limit, or validated physiological cutoff."
    )

    # Temporal rules
    strict_monotonicity: bool = Field(
        default=True,
        description="If True, subsequent timestamps must be strictly greater (>). If False, allows non-decreasing (>=)."
    )


class TelemetryValidator:
    """Validator ensuring telemetry and context samples adhere to physiological and physical constraints."""

    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or ValidationConfig()

    def _check_finite(self, value: Optional[float], field_name: str) -> None:
        """Verify that a numeric value is finite (not NaN or Inf)."""
        if value is None:
            return
        if not isinstance(value, (int, float)):
            raise NumericValueError(
                f"Field '{field_name}' must be numeric, got {type(value).__name__}",
                field=field_name,
                value=value,
            )
        if math.isnan(value) or math.isinf(value):
            raise NumericValueError(
                f"Field '{field_name}' must be finite (got {value})",
                field=field_name,
                value=value,
            )

    def validate_sample(
        self,
        sample: TelemetrySample,
        previous_timestamp: Optional[datetime] = None,
    ) -> TelemetrySample:
        """Validate a single TelemetrySample.
        
        Args:
            sample: The TelemetrySample to validate.
            previous_timestamp: Optional previous observation timestamp to verify monotonicity.
            
        Returns:
            The validated TelemetrySample.
            
        Raises:
            NumericValueError: If any numeric field is NaN or infinite.
            PhysiologicalPlausibilityError: If physiological metrics are biologically impossible.
            SensorConsistencyError: If partial multi-axis sensor data is supplied.
            TimestampMonotonicityError: If timestamps retrograde or are chronological violations.
        """
        # 1. Timestamp Monotonicity Check
        if previous_timestamp is not None:
            self._validate_timestamp_order(sample.timestamp, previous_timestamp)

        # 2. Check Numeric Finiteness across all numeric fields
        self._check_finite(sample.heart_rate, "heart_rate")
        self._check_finite(sample.spo2, "spo2")
        self._check_finite(sample.skin_temperature, "skin_temperature")
        self._check_finite(sample.battery_level, "battery_level")
        self._check_finite(sample.accel_x, "accel_x")
        self._check_finite(sample.accel_y, "accel_y")
        self._check_finite(sample.accel_z, "accel_z")
        if isinstance(sample.activity_level, (int, float)):
            self._check_finite(float(sample.activity_level), "activity_level")

        # 3. Heart Rate Physiological Plausibility
        if sample.heart_rate is not None:
            if not (self.config.hr_min <= sample.heart_rate <= self.config.hr_max):
                raise PhysiologicalPlausibilityError(
                    f"Heart rate {sample.heart_rate} BPM is outside plausible limits "
                    f"[{self.config.hr_min}, {self.config.hr_max}]",
                    field="heart_rate",
                    value=sample.heart_rate,
                )

        # 4. RR Interval Physiological Plausibility
        rr_intervals = sample.get_rr_intervals()
        for idx, rr in enumerate(rr_intervals):
            self._check_finite(rr, f"rr_interval[{idx}]")
            if not (self.config.rr_min_ms <= rr <= self.config.rr_max_ms):
                raise PhysiologicalPlausibilityError(
                    f"RR interval {rr} ms is outside plausible limits "
                    f"[{self.config.rr_min_ms}, {self.config.rr_max_ms}]",
                    field="rr_interval",
                    value=rr,
                )

        # 5. SpO2 Plausibility
        if sample.spo2 is not None:
            if not (self.config.spo2_min <= sample.spo2 <= self.config.spo2_max):
                raise PhysiologicalPlausibilityError(
                    f"SpO2 {sample.spo2}% is outside plausible limits "
                    f"[{self.config.spo2_min}, {self.config.spo2_max}]",
                    field="spo2",
                    value=sample.spo2,
                )

        # 6. Skin Temperature Plausibility
        if sample.skin_temperature is not None:
            if not (self.config.temp_min_c <= sample.skin_temperature <= self.config.temp_max_c):
                raise PhysiologicalPlausibilityError(
                    f"Skin temperature {sample.skin_temperature}°C is outside plausible limits "
                    f"[{self.config.temp_min_c}, {self.config.temp_max_c}]",
                    field="skin_temperature",
                    value=sample.skin_temperature,
                )

        # 7. Battery Level Plausibility
        if sample.battery_level is not None:
            if not (0.0 <= sample.battery_level <= 100.0):
                raise PhysiologicalPlausibilityError(
                    f"Battery level {sample.battery_level}% is outside valid range [0, 100]",
                    field="battery_level",
                    value=sample.battery_level,
                )

        # 8. Step Count Plausibility
        if sample.steps is not None and sample.steps < 0:
            raise NumericValueError(
                f"Step count cannot be negative (got {sample.steps})",
                field="steps",
                value=sample.steps,
            )

        # 9. Accelerometer Consistency & Plausibility
        self._validate_accelerometer(sample)

        return sample

    def _validate_accelerometer(self, sample: TelemetrySample) -> None:
        """Verify 3-axis accelerometer triplet consistency and physical limits."""
        axes = [sample.accel_x, sample.accel_y, sample.accel_z]
        non_none_count = sum(1 for a in axes if a is not None)

        # Partial triplet detection: either all 3 must be present or none
        if 0 < non_none_count < 3:
            raise SensorConsistencyError(
                f"Incomplete 3-axis accelerometer triplet: accel_x={sample.accel_x}, "
                f"accel_y={sample.accel_y}, accel_z={sample.accel_z}. All 3 axes must be provided.",
                field="accelerometer",
                value=(sample.accel_x, sample.accel_y, sample.accel_z),
            )

        if non_none_count == 3:
            for name, val in [("accel_x", sample.accel_x), ("accel_y", sample.accel_y), ("accel_z", sample.accel_z)]:
                assert val is not None
                if abs(val) > self.config.accel_axis_abs_max:
                    raise PhysiologicalPlausibilityError(
                        f"Accelerometer axis '{name}' value {val} exceeds maximum allowable magnitude "
                        f"({self.config.accel_axis_abs_max})",
                        field=name,
                        value=val,
                    )

    def _validate_timestamp_order(self, current: datetime, previous: datetime) -> None:
        """Verify chronological order between successive observations."""
        # Ensure consistent timezone awareness
        curr_tz = current.tzinfo is not None and current.tzinfo.utcoffset(current) is not None
        prev_tz = previous.tzinfo is not None and previous.tzinfo.utcoffset(previous) is not None

        if curr_tz != prev_tz:
            raise TimestampMonotonicityError(
                f"Cannot compare timezone-aware timestamp ({current}) with naive timestamp ({previous})",
                field="timestamp",
                value=current,
            )

        if self.config.strict_monotonicity:
            if current <= previous:
                raise TimestampMonotonicityError(
                    f"Timestamp must be strictly monotonic: current ({current}) <= previous ({previous})",
                    field="timestamp",
                    value=current,
                )
        else:
            if current < previous:
                raise TimestampMonotonicityError(
                    f"Timestamp must be non-decreasing: current ({current}) < previous ({previous})",
                    field="timestamp",
                    value=current,
                )

    def validate_context(
        self,
        context: OperationalContext,
        previous_timestamp: Optional[datetime] = None,
    ) -> OperationalContext:
        """Validate operational flight context parameters."""
        if previous_timestamp is not None:
            self._validate_timestamp_order(context.timestamp, previous_timestamp)

        self._check_finite(context.external_g_load, "external_g_load")
        self._check_finite(context.flight_duration_sec, "flight_duration_sec")
        self._check_finite(context.altitude_feet, "altitude_feet")
        self._check_finite(context.cabin_pressure_altitude_feet, "cabin_pressure_altitude_feet")

        if context.external_g_load is not None:
            if not (self.config.g_load_min <= context.external_g_load <= self.config.g_load_max):
                raise PhysiologicalPlausibilityError(
                    f"Operational G-load {context.external_g_load} is outside plausible range "
                    f"[{self.config.g_load_min}, {self.config.g_load_max}]",
                    field="external_g_load",
                    value=context.external_g_load,
                )

        if context.flight_duration_sec is not None and context.flight_duration_sec < 0:
            raise NumericValueError(
                f"Flight duration cannot be negative (got {context.flight_duration_sec})",
                field="flight_duration_sec",
                value=context.flight_duration_sec,
            )

        return context
