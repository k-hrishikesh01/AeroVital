"""Unit tests for Pilot Baseline Normalization Layer in AeroVital Core.

Tests cover:
1. Valid HR baseline comparison (positive delta)
2. Valid RMSSD baseline comparison (ratio)
3. Both comparisons simultaneously
4. Missing baseline (None)
5. Uncalibrated baseline (is_calibrated=False)
6. Missing / invalid baseline resting HR
7. Missing / invalid baseline RMSSD
8. Invalid zero or negative RMSSD baseline (division by zero safety)
9. Missing current window features
10. Partial baseline availability (HR only, RMSSD only)
11. baseline_available semantics (reflects profile presence, independent of field availability)
12. FeatureVector immutability (original instance unmutated, returns new instance)
13. PilotBaseline immutability (original profile unmutated)
14. Exact numerical precision
15. NaN / Inf safety (in window features, baseline values, or results)
16. Negative HR deviation (window HR below resting baseline)
"""

from datetime import datetime, timezone
import math
import pytest
from pydantic import ValidationError

from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.features import (
    BaselineComparisonFeatures,
    FeatureVector,
    HeartRateFeatures,
    HRVFeatures,
    MotionFeatures,
)
from backend.core.baseline.normalizer import BaselineNormalizer


# =====================================================================
# Fixtures & Helpers
# =====================================================================

@pytest.fixture
def now() -> datetime:
    """Fixed reference timestamp."""
    return datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_features(now: datetime) -> FeatureVector:
    """Helper to construct a raw FeatureVector with descriptive features."""
    return FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=75.0, min_hr=70.0, max_hr=80.0, hr_std=3.5),
        hrv_features=HRVFeatures(mean_rr_ms=800.0, rmssd_ms=30.0, valid_intervals_count=45),
        motion_features=MotionFeatures(mean_magnitude=1.02),
        baseline_features=BaselineComparisonFeatures(baseline_available=False),
    )


@pytest.fixture
def sample_baseline(now: datetime) -> PilotBaseline:
    """Helper to construct a calibrated PilotBaseline."""
    return PilotBaseline(
        pilot_id="PILOT-007",
        baseline_version="2026-v1.0",
        created_at=now,
        resting_heart_rate=60.0,
        baseline_rmssd=50.0,
        is_calibrated=True,
    )


# =====================================================================
# 1. Valid Comparisons
# =====================================================================

def test_valid_hr_baseline_comparison(sample_features, sample_baseline):
    """Verify exact delta HR calculation: mean_hr - resting_heart_rate."""
    normalizer = BaselineNormalizer()

    # Features: mean_hr = 75.0, Baseline: resting_hr = 60.0 -> delta = +15.0 BPM
    normalized = normalizer.normalize(sample_features, sample_baseline)

    assert normalized.baseline_features.baseline_available is True
    assert normalized.baseline_features.hr_deviation_from_baseline == 15.0


def test_valid_rmssd_baseline_comparison(sample_features, sample_baseline):
    """Verify exact RMSSD ratio calculation: rmssd_ms / baseline_rmssd."""
    normalizer = BaselineNormalizer()

    # Features: rmssd_ms = 30.0, Baseline: baseline_rmssd = 50.0 -> ratio = 0.60
    normalized = normalizer.normalize(sample_features, sample_baseline)

    assert normalized.baseline_features.baseline_available is True
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline == 0.60


def test_both_comparisons_simultaneously(sample_features, sample_baseline):
    """Verify both HR deviation and RMSSD ratio are populated in the new FeatureVector."""
    normalizer = BaselineNormalizer()

    normalized = normalizer.normalize(sample_features, sample_baseline)

    assert normalized.baseline_features.baseline_available is True
    assert normalized.baseline_features.hr_deviation_from_baseline == 15.0
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline == 0.60
    # Original descriptive features remain untouched
    assert normalized.hr_features.mean_hr == 75.0
    assert normalized.hrv_features.rmssd_ms == 30.0
    assert normalized.motion_features.mean_magnitude == 1.02


def test_negative_hr_deviation(sample_features, sample_baseline, now):
    """Verify signed difference when window mean HR is below resting baseline."""
    normalizer = BaselineNormalizer()

    # Window HR = 55.0, Resting HR = 60.0 -> delta = -5.0 BPM
    features_low_hr = FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=55.0),
    )

    normalized = normalizer.normalize(features_low_hr, sample_baseline)

    assert normalized.baseline_features.baseline_available is True
    assert normalized.baseline_features.hr_deviation_from_baseline == -5.0


# =====================================================================
# 2. Missing or Uncalibrated Baseline Profile
# =====================================================================

def test_missing_baseline_none(sample_features):
    """Verify that baseline=None yields baseline_available=False and all comparisons None."""
    normalizer = BaselineNormalizer()

    normalized = normalizer.normalize(sample_features, baseline=None)

    assert normalized.baseline_features.baseline_available is False
    assert normalized.baseline_features.hr_deviation_from_baseline is None
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline is None


def test_uncalibrated_baseline(sample_features, now):
    """Verify that is_calibrated=False yields baseline_available=False and all comparisons None."""
    uncalibrated = PilotBaseline(
        pilot_id="PILOT-007",
        baseline_version="2026-v1.0",
        created_at=now,
        resting_heart_rate=60.0,
        baseline_rmssd=50.0,
        is_calibrated=False,  # Incomplete calibration
    )

    normalizer = BaselineNormalizer()
    normalized = normalizer.normalize(sample_features, uncalibrated)

    assert normalized.baseline_features.baseline_available is False
    assert normalized.baseline_features.hr_deviation_from_baseline is None
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline is None


# =====================================================================
# 3. Partial Baseline Availability & Missing Operands
# =====================================================================

def test_missing_baseline_resting_hr(sample_features, now):
    """Verify invalid resting HR (<= 0) results in hr_deviation=None while RMSSD ratio evaluates."""
    baseline_invalid_hr = PilotBaseline(
        pilot_id="PILOT-007",
        baseline_version="2026-v1.0",
        created_at=now,
        resting_heart_rate=-10.0,  # Invalid
        baseline_rmssd=50.0,
        is_calibrated=True,
    )

    normalizer = BaselineNormalizer()
    normalized = normalizer.normalize(sample_features, baseline_invalid_hr)

    assert normalized.baseline_features.baseline_available is True
    assert normalized.baseline_features.hr_deviation_from_baseline is None
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline == 0.60


def test_missing_baseline_rmssd(sample_features, now):
    """Verify baseline with baseline_rmssd=None yields rmssd_ratio=None while HR delta evaluates."""
    baseline_no_rmssd = PilotBaseline(
        pilot_id="PILOT-007",
        baseline_version="2026-v1.0",
        created_at=now,
        resting_heart_rate=60.0,
        baseline_rmssd=None,  # No HRV calibration
        is_calibrated=True,
    )

    normalizer = BaselineNormalizer()
    normalized = normalizer.normalize(sample_features, baseline_no_rmssd)

    assert normalized.baseline_features.baseline_available is True
    assert normalized.baseline_features.hr_deviation_from_baseline == 15.0
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline is None


def test_invalid_zero_or_negative_baseline_rmssd(sample_features, now):
    """Verify baseline_rmssd <= 0 yields rmssd_ratio=None to prevent division by zero or invalid ratios."""
    normalizer = BaselineNormalizer()

    # Zero RMSSD
    b_zero = PilotBaseline(
        pilot_id="PILOT-007",
        baseline_version="2026-v1.0",
        created_at=now,
        resting_heart_rate=60.0,
        baseline_rmssd=0.0,
        is_calibrated=True,
    )
    norm_zero = normalizer.normalize(sample_features, b_zero)
    assert norm_zero.baseline_features.hrv_rmssd_ratio_to_baseline is None

    # Negative RMSSD
    b_neg = PilotBaseline(
        pilot_id="PILOT-007",
        baseline_version="2026-v1.0",
        created_at=now,
        resting_heart_rate=60.0,
        baseline_rmssd=-25.0,
        is_calibrated=True,
    )
    norm_neg = normalizer.normalize(sample_features, b_neg)
    assert norm_neg.baseline_features.hrv_rmssd_ratio_to_baseline is None


def test_missing_current_window_features(sample_baseline, now):
    """Verify that when window features are None, respective comparisons are None while baseline_available is True."""
    empty_features = FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=None),
        hrv_features=HRVFeatures(rmssd_ms=None),
    )

    normalizer = BaselineNormalizer()
    normalized = normalizer.normalize(empty_features, sample_baseline)

    assert normalized.baseline_features.baseline_available is True
    assert normalized.baseline_features.hr_deviation_from_baseline is None
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline is None


def test_baseline_available_semantics(sample_baseline, now):
    """Verify baseline_available=True reflects profile availability, even when NO comparisons are calculable."""
    # Window has NO features at all
    no_features = FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
    )

    normalizer = BaselineNormalizer()
    normalized = normalizer.normalize(no_features, sample_baseline)

    # Profile was provided and calibrated
    assert normalized.baseline_features.baseline_available is True
    # But individual metrics cannot be evaluated
    assert normalized.baseline_features.hr_deviation_from_baseline is None
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline is None


# =====================================================================
# 4. Immutability
# =====================================================================

def test_feature_vector_immutability(sample_features, sample_baseline):
    """Verify original FeatureVector is never mutated and normalizer returns a new distinct instance."""
    original_baseline_avail = sample_features.baseline_features.baseline_available
    original_hr_dev = sample_features.baseline_features.hr_deviation_from_baseline

    normalizer = BaselineNormalizer()
    normalized = normalizer.normalize(sample_features, sample_baseline)

    # 1. Returned object is a distinct instance
    assert normalized is not sample_features

    # 2. Original FeatureVector remains strictly unmutated
    assert sample_features.baseline_features.baseline_available == original_baseline_avail
    assert sample_features.baseline_features.hr_deviation_from_baseline == original_hr_dev

    # 3. Pydantic model is frozen
    with pytest.raises((ValidationError, TypeError)):
        sample_features.baseline_features = BaselineComparisonFeatures(baseline_available=True)  # type: ignore


def test_pilot_baseline_immutability(sample_features, sample_baseline):
    """Verify PilotBaseline profile is never mutated during normalization."""
    original_resting_hr = sample_baseline.resting_heart_rate
    original_rmssd = sample_baseline.baseline_rmssd

    normalizer = BaselineNormalizer()
    _ = normalizer.normalize(sample_features, sample_baseline)

    assert sample_baseline.resting_heart_rate == original_resting_hr
    assert sample_baseline.baseline_rmssd == original_rmssd

    with pytest.raises((ValidationError, TypeError)):
        sample_baseline.resting_heart_rate = 70.0  # type: ignore


# =====================================================================
# 5. Numerical Precision & NaN / Inf Safety
# =====================================================================

def test_exact_numerical_precision(now):
    """Verify exact arithmetic without truncation or precision corruption."""
    features = FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=72.5),
        hrv_features=HRVFeatures(rmssd_ms=42.0),
    )
    baseline = PilotBaseline(
        pilot_id="PILOT-007",
        baseline_version="2026-v1.0",
        created_at=now,
        resting_heart_rate=58.0,
        baseline_rmssd=56.0,
        is_calibrated=True,
    )

    normalizer = BaselineNormalizer()
    normalized = normalizer.normalize(features, baseline)

    # 72.5 - 58.0 = 14.5
    assert normalized.baseline_features.hr_deviation_from_baseline == 14.5
    # 42.0 / 56.0 = 0.75
    assert normalized.baseline_features.hrv_rmssd_ratio_to_baseline == 0.75


def test_nan_and_inf_safety(now):
    """Verify non-finite operands safely evaluate to None without exceptions."""
    normalizer = BaselineNormalizer()

    # NaN in window HR
    f_nan_hr = FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=float("nan")),
        hrv_features=HRVFeatures(rmssd_ms=30.0),
    )
    b_valid = PilotBaseline(
        pilot_id="PILOT-007",
        baseline_version="2026-v1.0",
        created_at=now,
        resting_heart_rate=60.0,
        baseline_rmssd=50.0,
        is_calibrated=True,
    )
    norm_nan_hr = normalizer.normalize(f_nan_hr, b_valid)
    assert norm_nan_hr.baseline_features.hr_deviation_from_baseline is None
    assert norm_nan_hr.baseline_features.hrv_rmssd_ratio_to_baseline == 0.60

    # Inf in window RMSSD
    f_inf_rmssd = FeatureVector(
        window_start=now,
        window_end=now,
        window_duration_sec=60.0,
        hr_features=HeartRateFeatures(mean_hr=75.0),
        hrv_features=HRVFeatures(rmssd_ms=float("inf")),
    )
    norm_inf_rmssd = normalizer.normalize(f_inf_rmssd, b_valid)
    assert norm_inf_rmssd.baseline_features.hr_deviation_from_baseline == 15.0
    assert norm_inf_rmssd.baseline_features.hrv_rmssd_ratio_to_baseline is None
