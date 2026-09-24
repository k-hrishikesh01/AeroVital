"""Unit tests for Feature Extraction Layer in AeroVital Core.

Tests cover:
1. retained_indices correctness
2. RMSSD excludes gaps caused by rejected RR intervals
3. pNN50 excludes gaps caused by rejected RR intervals
4. exact mean RR
5. exact sample SDNN
6. exact RMSSD
7. exact pNN50
8. exact mean/min/max HR
9. exact sample HR standard deviation
10. exact HR range
11. exact OLS HR trend
12. BPM/minute conversion
13. BPM/second output
14. acceleration magnitude
15. acceleration variance
16. peak magnitude
17. activity intensity with G
18. activity intensity with m/s²
19. activity intensity with UNSPECIFIED
20. operational minimums override mathematical minimums
21. mathematical minimums with permissive configuration
22. empty inputs
23. insufficient data
24. missing/partial accelerometer triplets
25. baseline features remain unavailable
26. source data remains unmutated
"""

from datetime import datetime, timedelta, timezone
import math
import pytest
from pydantic import ValidationError

from backend.core.quality.rules import AccelUnit
from backend.core.schemas.telemetry import TelemetrySample
from backend.core.preprocessing.cleaner import RRCleaner, RRCleaningConfig
from backend.core.preprocessing.windowing import WindowBuffer, WindowConfig, WindowSnapshot
from backend.core.features.config import FeatureConfig, HRTrendUnit
from backend.core.features.extractor import FeatureExtractor


# =====================================================================
# Fixtures & Helpers
# =====================================================================

@pytest.fixture
def base_time() -> datetime:
    """Deterministic reference timestamp."""
    return datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


def make_sample(
    timestamp: datetime,
    heart_rate: float | None = 72.0,
    rr_interval: float | list[float] | None = 833.0,
    accel: tuple[float, float, float] | None = (0.0, 0.0, 1.0),
) -> TelemetrySample:
    """Helper to construct frozen TelemetrySample instances."""
    return TelemetrySample(
        timestamp=timestamp,
        heart_rate=heart_rate,
        rr_interval=rr_interval,
        accel_x=accel[0] if accel is not None else None,
        accel_y=accel[1] if accel is not None else None,
        accel_z=accel[2] if accel is not None else None,
    )


# =====================================================================
# 1. Retained Indices & Adjacency Integrity (Provenance Contract)
# =====================================================================

def test_retained_indices_correctness():
    """Verify that cleaner records exact 0-based indices of retained intervals in raw sequence."""
    cleaner = RRCleaner()
    # Indices: 0: valid, 1: NaN, 2: valid, 3: out-of-bounds low, 4: valid
    raw = [800.0, float("nan"), 810.0, 100.0, 820.0]

    result = cleaner.clean_intervals(raw)

    assert result.cleaned_intervals == [800.0, 810.0, 820.0]
    assert result.retained_indices == [0, 2, 4]
    assert len(result.cleaned_intervals) == len(result.retained_indices)


def test_rmssd_excludes_gaps_caused_by_rejected_intervals(base_time):
    """Verify RMSSD does NOT compute successive differences across gaps created by rejected artifacts.
    
    Sequence: [800.0, 810.0, NaN (rejected), 900.0, 910.0]
    Valid consecutive pairs:
    - (800.0, 810.0) -> index 0, 1 (consecutive, diff = 10)
    - (810.0, 900.0) -> index 1, 3 (NOT consecutive, gap excluded!)
    - (900.0, 910.0) -> index 3, 4 (consecutive, diff = 10)
    Expected RMSSD: sqrt((10^2 + 10^2) / 2) = 10.0 ms.
    If the gap between 810 and 900 were included, diff would be 90, yielding RMSSD ~ 52.6 ms.
    """
    extractor = FeatureExtractor(
        config=FeatureConfig(min_rr_samples_for_hrv=4, min_consecutive_rr_pairs=2)
    )

    # 4 clean intervals, 1 rejected NaN in middle
    raw_rr = [800.0, 810.0, float("nan"), 900.0, 910.0]
    samples = [
        make_sample(base_time + timedelta(seconds=i), rr_interval=rr)
        for i, rr in enumerate(raw_rr)
    ]

    fv = extractor.extract_from_samples(samples)

    assert fv.hrv_features.valid_intervals_count == 4
    # Genuinely consecutive diffs are strictly [10.0, 10.0]
    assert fv.hrv_features.rmssd_ms is not None
    assert pytest.approx(fv.hrv_features.rmssd_ms, 1e-6) == 10.0


def test_pnn50_excludes_gaps_caused_by_rejected_intervals(base_time):
    """Verify pNN50 does NOT count >50ms differences that span across artifact gaps.
    
    In [800.0, 810.0, NaN, 900.0, 910.0]:
    The jump from 810.0 to 900.0 is 90ms (> 50ms), but it spans an artifact gap.
    The genuinely consecutive pairs are (800, 810) -> 10ms, (900, 910) -> 10ms.
    Neither consecutive pair exceeds 50ms.
    Expected pNN50: 0.0%.
    If gap were erroneously counted, pNN50 would be 1/3 (33.3%).
    """
    extractor = FeatureExtractor(
        config=FeatureConfig(min_rr_samples_for_hrv=4, min_consecutive_rr_pairs=2)
    )

    raw_rr = [800.0, 810.0, float("nan"), 900.0, 910.0]
    samples = [
        make_sample(base_time + timedelta(seconds=i), rr_interval=rr)
        for i, rr in enumerate(raw_rr)
    ]

    fv = extractor.extract_from_samples(samples)

    assert fv.hrv_features.pnn50_percent is not None
    assert fv.hrv_features.pnn50_percent == 0.0


# =====================================================================
# 2. Exact Mathematical Correctness for HRV Features
# =====================================================================

def test_exact_hrv_metrics(base_time):
    """Verify exact calculation of mean RR, sample SDNN, RMSSD, and pNN50 on known values."""
    # 5 intervals: 800.0, 820.0, 760.0, 840.0, 780.0
    # Mean: (800 + 820 + 760 + 840 + 780) / 5 = 4000 / 5 = 800.0
    # Deviations from 800: [0, 20, -40, 40, -20]
    # Sum of squared deviations: 0 + 400 + 1600 + 1600 + 400 = 4000
    # Sample variance (N - 1 = 4): 4000 / 4 = 1000
    # SDNN: sqrt(1000) = 31.6227766...
    # Successive diffs (all consecutive):
    # 820 - 800 = 20
    # 760 - 820 = -60 (|diff| = 60 > 50 -> counts for pNN50)
    # 840 - 760 = 80 (|diff| = 80 > 50 -> counts for pNN50)
    # 780 - 840 = -60 (|diff| = 60 > 50 -> counts for pNN50)
    # Consecutive diffs: [20, -60, 80, -60], count P = 4
    # Squared diffs: 400 + 3600 + 6400 + 3600 = 14000
    # RMSSD: sqrt(14000 / 4) = sqrt(3500) = 59.1607978...
    # pNN50: 3 out of 4 diffs > 50ms = (3 / 4) * 100% = 75.0%
    extractor = FeatureExtractor(
        config=FeatureConfig(min_rr_samples_for_hrv=5, min_consecutive_rr_pairs=3)
    )

    rr_vals = [800.0, 820.0, 760.0, 840.0, 780.0]
    samples = [make_sample(base_time + timedelta(seconds=i), rr_interval=rr) for i, rr in enumerate(rr_vals)]

    fv = extractor.extract_from_samples(samples)
    hrv = fv.hrv_features

    assert hrv.valid_intervals_count == 5
    assert hrv.mean_rr_ms == 800.0
    assert pytest.approx(hrv.sdnn_ms, 1e-5) == math.sqrt(1000.0)
    assert pytest.approx(hrv.rmssd_ms, 1e-5) == math.sqrt(3500.0)
    assert pytest.approx(hrv.pnn50_percent, 1e-5) == 75.0


# =====================================================================
# 3. Exact Mathematical Correctness for HR Dynamics
# =====================================================================

def test_exact_hr_dynamics_and_range(base_time):
    """Verify exact mean HR, min HR, max HR, sample HR std, and HR range on known values."""
    # 4 samples: 60.0, 70.0, 80.0, 90.0
    # Mean: 300 / 4 = 75.0
    # Min: 60.0, Max: 90.0, Range: 30.0
    # Deviations: [-15, -5, 5, 15]
    # Sum sq dev: 225 + 25 + 25 + 225 = 500
    # Sample variance (M - 1 = 3): 500 / 3 = 166.6666...
    # Sample std: sqrt(500 / 3) = 12.909944...
    extractor = FeatureExtractor(config=FeatureConfig(min_hr_samples_for_dynamics=3))

    hr_vals = [60.0, 70.0, 80.0, 90.0]
    samples = [make_sample(base_time + timedelta(seconds=i), heart_rate=hr) for i, hr in enumerate(hr_vals)]

    fv = extractor.extract_from_samples(samples)
    hr_feat = fv.hr_features

    assert hr_feat.mean_hr == 75.0
    assert hr_feat.min_hr == 60.0
    assert hr_feat.max_hr == 90.0
    assert hr_feat.hr_range == 30.0
    assert pytest.approx(hr_feat.hr_std, 1e-5) == math.sqrt(500.0 / 3.0)


def test_exact_ols_hr_trend_bpm_per_minute(base_time):
    """Verify OLS linear trend slope scaled to BPM/minute.
    
    Timestamps: t = 0s, 10s, 20s, 30s.
    Heart rates: HR = 70, 72, 74, 76.
    Exact linear relationship: HR(t) = 70 + 0.2 * t.
    Slope = 0.2 BPM/second.
    In BPM/minute: 0.2 * 60 = 12.0 BPM/minute.
    """
    config = FeatureConfig(
        min_hr_samples_for_dynamics=3,
        hr_trend_unit=HRTrendUnit.BPM_PER_MINUTE,
    )
    extractor = FeatureExtractor(config=config)

    samples = [
        make_sample(base_time, heart_rate=70.0),
        make_sample(base_time + timedelta(seconds=10), heart_rate=72.0),
        make_sample(base_time + timedelta(seconds=20), heart_rate=74.0),
        make_sample(base_time + timedelta(seconds=30), heart_rate=76.0),
    ]

    fv = extractor.extract_from_samples(samples)

    assert fv.hr_features.hr_trend is not None
    assert pytest.approx(fv.hr_features.hr_trend, 1e-5) == 12.0


def test_exact_ols_hr_trend_bpm_per_second(base_time):
    """Verify OLS linear trend slope with BPM/second unit selection."""
    config = FeatureConfig(
        min_hr_samples_for_dynamics=3,
        hr_trend_unit=HRTrendUnit.BPM_PER_SECOND,
    )
    extractor = FeatureExtractor(config=config)

    samples = [
        make_sample(base_time, heart_rate=70.0),
        make_sample(base_time + timedelta(seconds=10), heart_rate=72.0),
        make_sample(base_time + timedelta(seconds=20), heart_rate=74.0),
        make_sample(base_time + timedelta(seconds=30), heart_rate=76.0),
    ]

    fv = extractor.extract_from_samples(samples)

    assert fv.hr_features.hr_trend is not None
    assert pytest.approx(fv.hr_features.hr_trend, 1e-5) == 0.2


def test_hr_trend_with_zero_temporal_variance(base_time):
    """Verify OLS slope returns None when all samples have identical timestamps (zero denominator)."""
    extractor = FeatureExtractor(config=FeatureConfig(min_hr_samples_for_dynamics=2))

    samples = [
        make_sample(base_time, heart_rate=70.0),
        make_sample(base_time, heart_rate=75.0),
    ]

    fv = extractor.extract_from_samples(samples)
    assert fv.hr_features.hr_trend is None


# =====================================================================
# 4. Exact Mathematical Correctness for Motion & Strict Unit Contract
# =====================================================================

def test_exact_motion_features_with_g_unit(base_time):
    """Verify acceleration magnitude, sample variance, peak magnitude, and activity intensity with G.
    
    Triplets:
    (0, 0, 1) -> mag = 1.0
    (0, 0, 2) -> mag = 2.0
    (1, 2, 2) -> mag = sqrt(1 + 4 + 4) = 3.0
    Magnitudes: [1.0, 2.0, 3.0]
    Mean mag: (1 + 2 + 3) / 3 = 2.0
    Peak mag: 3.0
    Sample variance (K - 1 = 2): ((1-2)^2 + (2-2)^2 + (3-2)^2) / 2 = 2 / 2 = 1.0
    Activity intensity with AccelUnit.G (ref = 1.0):
    |1 - 1| = 0
    |2 - 1| = 1
    |3 - 1| = 2
    Mean intensity: (0 + 1 + 2) / 3 = 1.0
    """
    config = FeatureConfig(
        min_accel_samples_for_motion=3,
        accel_unit=AccelUnit.G,
    )
    extractor = FeatureExtractor(config=config)

    samples = [
        make_sample(base_time, accel=(0.0, 0.0, 1.0)),
        make_sample(base_time + timedelta(seconds=1), accel=(0.0, 0.0, 2.0)),
        make_sample(base_time + timedelta(seconds=2), accel=(1.0, 2.0, 2.0)),
    ]

    fv = extractor.extract_from_samples(samples)
    motion = fv.motion_features

    assert motion.mean_magnitude == 2.0
    assert motion.peak_magnitude == 3.0
    assert motion.variance_magnitude == 1.0
    assert motion.activity_intensity == 1.0


def test_activity_intensity_with_m_s2_unit(base_time):
    """Verify activity intensity uses 9.80665 when AccelUnit.M_S2 is declared.
    
    Triplets with mag = [9.80665, 11.80665, 7.80665]
    Deviations from 9.80665: |0|, |2.0|, |-2.0| -> [0, 2.0, 2.0]
    Mean intensity: 4.0 / 3 = 1.333333...
    """
    config = FeatureConfig(
        min_accel_samples_for_motion=3,
        accel_unit=AccelUnit.M_S2,
    )
    extractor = FeatureExtractor(config=config)

    samples = [
        make_sample(base_time, accel=(0.0, 0.0, 9.80665)),
        make_sample(base_time + timedelta(seconds=1), accel=(0.0, 0.0, 11.80665)),
        make_sample(base_time + timedelta(seconds=2), accel=(0.0, 0.0, 7.80665)),
    ]

    fv = extractor.extract_from_samples(samples)

    assert fv.motion_features.activity_intensity is not None
    assert pytest.approx(fv.motion_features.activity_intensity, 1e-5) == 4.0 / 3.0


def test_activity_intensity_with_unspecified_unit_returns_none(base_time):
    """Verify strict contract: AccelUnit.UNSPECIFIED yields None for activity intensity (no unit guessing)."""
    config = FeatureConfig(
        min_accel_samples_for_motion=3,
        accel_unit=AccelUnit.UNSPECIFIED,
    )
    extractor = FeatureExtractor(config=config)

    samples = [
        make_sample(base_time, accel=(0.0, 0.0, 1.0)),
        make_sample(base_time + timedelta(seconds=1), accel=(0.0, 0.0, 1.1)),
        make_sample(base_time + timedelta(seconds=2), accel=(0.0, 0.0, 0.9)),
    ]

    fv = extractor.extract_from_samples(samples)

    assert fv.motion_features.mean_magnitude is not None
    # Strictly None because unit is UNSPECIFIED
    assert fv.motion_features.activity_intensity is None


def test_missing_and_partial_accelerometer_triplets_ignored(base_time):
    """Verify incomplete accelerometer triplets (where any axis is None) are completely skipped."""
    extractor = FeatureExtractor(config=FeatureConfig(min_accel_samples_for_motion=2))

    # 1 complete, 2 incomplete triplets
    s1 = make_sample(base_time, accel=(0.0, 0.0, 1.0))
    s2 = TelemetrySample(timestamp=base_time + timedelta(seconds=1), accel_x=0.1, accel_y=None, accel_z=0.9)
    s3 = TelemetrySample(timestamp=base_time + timedelta(seconds=2), accel_x=None, accel_y=0.2, accel_z=0.9)

    fv = extractor.extract_from_samples([s1, s2, s3])

    # Only 1 valid triplet found, but min_accel_samples_for_motion is 2 -> returns None
    assert fv.motion_features.mean_magnitude is None


# =====================================================================
# 5. Operational Minimums vs. Mathematical Minimums
# =====================================================================

def test_operational_minimums_override_mathematical_minimums(base_time):
    """Verify that feature extraction respects operational minimums even if mathematical minimum is met.
    
    SDNN is mathematically defined for N >= 2, but FeatureConfig defaults to min_rr_samples_for_hrv = 5.
    With 3 clean intervals, mathematical formula could run, but operational minimum must suppress it to None.
    """
    extractor = FeatureExtractor(config=FeatureConfig(min_rr_samples_for_hrv=5))

    samples = [
        make_sample(base_time, rr_interval=800.0),
        make_sample(base_time + timedelta(seconds=1), rr_interval=820.0),
        make_sample(base_time + timedelta(seconds=2), rr_interval=810.0),
    ]

    fv = extractor.extract_from_samples(samples)

    # Valid intervals count is reported
    assert fv.hrv_features.valid_intervals_count == 3
    # All summary HRV features suppressed to None
    assert fv.hrv_features.mean_rr_ms is None
    assert fv.hrv_features.sdnn_ms is None
    assert fv.hrv_features.rmssd_ms is None
    assert fv.hrv_features.pnn50_percent is None


def test_permissive_operational_configuration(base_time):
    """Verify that lowering operational minimums in FeatureConfig allows extraction on smaller samples."""
    permissive_config = FeatureConfig(
        min_rr_samples_for_hrv=2,
        min_consecutive_rr_pairs=1,
    )
    extractor = FeatureExtractor(config=permissive_config)

    samples = [
        make_sample(base_time, rr_interval=800.0),
        make_sample(base_time + timedelta(seconds=1), rr_interval=820.0),
    ]

    fv = extractor.extract_from_samples(samples)

    assert fv.hrv_features.valid_intervals_count == 2
    assert fv.hrv_features.mean_rr_ms == 810.0
    assert fv.hrv_features.sdnn_ms is not None
    assert fv.hrv_features.rmssd_ms is not None


# =====================================================================
# 6. Empty and Insufficient Windows
# =====================================================================

def test_empty_window_behavior():
    """Verify feature extractor handles empty input without exceptions, returning all None features."""
    extractor = FeatureExtractor()

    fv = extractor.extract_from_samples([])

    assert fv.window_duration_sec == 0.0
    assert fv.hr_features.mean_hr is None
    assert fv.hrv_features.valid_intervals_count == 0
    assert fv.hrv_features.rmssd_ms is None
    assert fv.motion_features.mean_magnitude is None
    assert fv.baseline_features.baseline_available is False


def test_snapshot_extraction(base_time):
    """Verify extract_features works seamlessly on a WindowSnapshot."""
    config = WindowConfig(window_duration_sec=30.0)
    buffer = WindowBuffer(config)

    for i in range(5):
        buffer.add_sample(make_sample(
            base_time + timedelta(seconds=i),
            heart_rate=70.0 + i,
            rr_interval=800.0 + (i * 10),
            accel=(0.0, 0.0, 1.0),
        ))

    snapshot = buffer.snapshot()
    assert snapshot is not None

    extractor = FeatureExtractor(config=FeatureConfig(accel_unit=AccelUnit.G))
    fv = extractor.extract_features(snapshot)

    assert fv.window_start == base_time
    assert fv.window_end == base_time + timedelta(seconds=4)
    assert fv.window_duration_sec == 4.0
    assert fv.hr_features.mean_hr == 72.0
    assert fv.hrv_features.valid_intervals_count == 5
    assert fv.motion_features.mean_magnitude == 1.0


# =====================================================================
# 7. Layer Separation: Baseline Features Remain Unavailable
# =====================================================================

def test_baseline_features_remain_strictly_unavailable(base_time):
    """Verify that FeatureExtractor never calculates baseline comparisons (reserved for Step 6)."""
    extractor = FeatureExtractor()

    samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(10)]
    fv = extractor.extract_from_samples(samples)

    assert fv.baseline_features.baseline_available is False
    assert fv.baseline_features.hr_deviation_from_baseline is None
    assert fv.baseline_features.hrv_rmssd_ratio_to_baseline is None


# =====================================================================
# 8. Source Data Immutability
# =====================================================================

def test_source_data_remains_unmutated(base_time):
    """Verify neither FeatureExtractor nor cleaner mutates incoming samples or lists."""
    sample = make_sample(base_time, heart_rate=75.0, rr_interval=[800.0, 810.0])
    raw_list = [sample]

    extractor = FeatureExtractor()
    _ = extractor.extract_from_samples(raw_list)

    # Sample attributes unchanged
    assert sample.heart_rate == 75.0
    assert sample.rr_interval == [800.0, 810.0]
    # Input list length unchanged
    assert len(raw_list) == 1
    assert raw_list[0] is sample
