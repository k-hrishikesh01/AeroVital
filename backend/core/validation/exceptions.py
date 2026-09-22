"""Validation Exceptions for AeroVital Core.

Structured exception hierarchy for signal validation failures:
physiological out-of-bounds, timestamp monotonicity violations,
invalid numerical values (NaN/Inf), and sensor consistency errors.
"""

from typing import Any, Optional


class SignalValidationError(ValueError):
    """Base exception for all signal validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class PhysiologicalPlausibilityError(SignalValidationError):
    """Raised when a physiological measurement falls outside plausible biological limits."""
    pass


class TimestampMonotonicityError(SignalValidationError):
    """Raised when sample timestamps retrograde or arrive out of chronological order."""
    pass


class NumericValueError(SignalValidationError):
    """Raised when numeric data is non-finite (NaN, Infinity) or violates basic domain logic."""
    pass


class SensorConsistencyError(SignalValidationError):
    """Raised when interrelated sensor channels are inconsistent (e.g. partial accelerometer axes)."""
    pass
