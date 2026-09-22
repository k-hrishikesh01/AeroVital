"""AeroVital Signal Validation Layer.

Exports validator components and validation exceptions.
"""

from backend.core.validation.exceptions import (
    SignalValidationError,
    PhysiologicalPlausibilityError,
    TimestampMonotonicityError,
    NumericValueError,
    SensorConsistencyError,
)
from backend.core.validation.validator import (
    ValidationConfig,
    TelemetryValidator,
)

__all__ = [
    "SignalValidationError",
    "PhysiologicalPlausibilityError",
    "TimestampMonotonicityError",
    "NumericValueError",
    "SensorConsistencyError",
    "ValidationConfig",
    "TelemetryValidator",
]
