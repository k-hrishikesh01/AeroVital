"""Unit tests for Preprocessing and Windowing Layer in AeroVital Core.

Tests cover:
1. clean RR intervals remain unchanged
2. malformed/non-finite RR values are rejected or handled according to the existing validation contract
3. obvious RR artifacts are handled deterministically
4. no fabricated RR values
5. scalar and list RR compatibility
6. chronological ordering
7. window insertion
8. samples leaving the rolling window
9. configurable window duration
10. configurable step
11. irregular timestamps/gaps
12. empty and insufficient windows
13. no mutation of the original telemetry samples
"""

import math
from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from backend.core.schemas.telemetry import TelemetrySample
from backend.core.preprocessing.cleaner import (
    RRCleaner,
    RRCleaningConfig,
    RRCleaningResult,
)
from backend.core.preprocessing.windowing import (
    WindowBuffer,
    WindowConfig,
    WindowSnapshot,
    slide_windows,
)


# =====================================================================
# Fixtures & Helpers
# =====================================================================

@pytest.fixture
def base_time() -> datetime:
    """Fixed reference timestamp for deterministic window tests."""
    return datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


def make_sample(
    timestamp: datetime,
    heart_rate: float = 72.0,
    rr_interval: float | list[float] | None = 833.0,
    accel_z: float | None = 1.0,
) -> TelemetrySample:
    """Helper to construct frozen TelemetrySample instances."""
    return TelemetrySample(
        timestamp=timestamp,
        heart_rate=heart_rate,
        rr_interval=rr_interval,
        accel_x=0.0 if accel_z is not None else None,
        accel_y=0.0 if accel_z is not None else None,
        accel_z=accel_z,
    )


# =====================================================================
# 1. Clean RR intervals remain unchanged
# =====================================================================

def test_clean_rr_intervals_remain_unchanged():
    """Verify that a sequence of physiologically normal intervals is preserved exactly."""
    cleaner = RRCleaner()
    raw = [800.0, 810.0, 795.0, 805.0, 820.0, 815.0]

    result = cleaner.clean_intervals(raw)

    assert result.raw_count == len(raw)
    assert result.valid_count == len(raw)
    assert result.cleaned_intervals == raw
    assert len(result.rejected_intervals) == 0
    assert result.rejection_ratio == 0.0


def test_clean_rr_integers_converted_to_float_faithfully():
    """Verify integer inputs are faithfully converted to float without value modification."""
    cleaner = RRCleaner()
    raw = [800, 810, 820]

    result = cleaner.clean_intervals(raw)

    assert result.cleaned_intervals == [800.0, 810.0, 820.0]
    assert result.valid_count == 3


# =====================================================================
# 2. Malformed / Non-finite RR values handling
# =====================================================================

def test_non_finite_rr_values_rejected():
    """Verify NaN, +Inf, -Inf, and non-numeric types are identified and rejected."""
    cleaner = RRCleaner()
    raw = [800.0, float("nan"), 810.0, float("inf"), float("-inf"), "corrupt_string", None, 820.0]

    result = cleaner.clean_intervals(raw)

    assert result.raw_count == 8
    assert result.valid_count == 3
    assert result.cleaned_intervals == [800.0, 810.0, 820.0]
    assert len(result.rejected_intervals) == 5
    for val, reason in result.rejected_intervals:
        assert reason == "NON_FINITE"


def test_out_of_bounds_rr_rejected():
    """Verify values outside [min_rr_ms, max_rr_ms] are rejected with specific reasons."""
    config = RRCleaningConfig(min_rr_ms=300.0, max_rr_ms=2000.0)
    cleaner = RRCleaner(config)
    raw = [200.0, 800.0, 2500.0, 1000.0]

    result = cleaner.clean_intervals(raw)

    assert result.cleaned_intervals == [800.0, 1000.0]
    assert result.valid_count == 2
    rejections = dict(result.rejected_intervals)
    assert rejections[200.0] == "OUT_OF_BOUNDS_LOW"
    assert rejections[2500.0] == "OUT_OF_BOUNDS_HIGH"


# =====================================================================
# 3. Obvious RR artifacts handled deterministically
# =====================================================================

def test_excessive_successive_diff_rejected():
    """Verify relative jump exceeding max_successive_diff_ratio is suppressed."""
    config = RRCleaningConfig(max_successive_diff_ratio=0.30)
    cleaner = RRCleaner(config)

    # 800 -> 1200 is a 50% jump (> 30%) -> artifact
    # 800 -> 850 is a 6.25% jump (< 30%) -> valid
    raw = [800.0, 1200.0, 850.0]

    result = cleaner.clean_intervals(raw)

    assert result.cleaned_intervals == [800.0, 850.0]
    assert result.valid_count == 2
    assert len(result.rejected_intervals) == 1
    assert result.rejected_intervals[0] == (1200.0, "EXCESSIVE_SUCCESSIVE_DIFF")


def test_consecutive_artifacts_do_not_poison_subsequent_valid_beats():
    """Verify that multiple artifacts in a row are rejected and valid beats recover."""
    config = RRCleaningConfig(max_successive_diff_ratio=0.30)
    cleaner = RRCleaner(config)

    # 800.0 is baseline.
    # 1300.0 (jump 62.5% > 30% -> reject)
    # 1400.0 (compared to last valid 800.0 -> jump 75% > 30% -> reject)
    # 810.0 (compared to last valid 800.0 -> jump 1.25% < 30% -> accept)
    raw = [800.0, 1300.0, 1400.0, 810.0]

    result = cleaner.clean_intervals(raw)

    assert result.cleaned_intervals == [800.0, 810.0]
    assert result.valid_count == 2
    assert len(result.rejected_intervals) == 2


# =====================================================================
# 4. No fabricated RR values
# =====================================================================

def test_no_fabricated_rr_values():
    """Verify that cleaned output is strictly a subset of input; never interpolated or imputed."""
    cleaner = RRCleaner()
    raw = [800.0, float("nan"), 100.0, 820.0]

    result = cleaner.clean_intervals(raw)

    # Only 800.0 and 820.0 should exist; no replacement for NaN or 100.0
    assert result.cleaned_intervals == [800.0, 820.0]
    for clean_val in result.cleaned_intervals:
        assert clean_val in raw


def test_empty_input_produces_empty_output_without_fabrication():
    """Verify empty input produces zero intervals without synthetic data."""
    cleaner = RRCleaner()
    result = cleaner.clean_intervals([])

    assert result.raw_count == 0
    assert result.valid_count == 0
    assert result.cleaned_intervals == []
    assert result.rejected_intervals == []
    assert result.rejection_ratio == 0.0


# =====================================================================
# 5. Scalar and List RR compatibility
# =====================================================================

def test_scalar_and_list_rr_in_samples(base_time):
    """Verify compatibility with both scalar and list RR representations via TelemetrySample."""
    cleaner = RRCleaner()

    sample_scalar = make_sample(base_time, rr_interval=850.0)
    sample_list = make_sample(base_time + timedelta(seconds=1), rr_interval=[845.0, 855.0])
    sample_none = make_sample(base_time + timedelta(seconds=2), rr_interval=None)

    # Individual cleaning
    res_scalar = cleaner.clean_sample(sample_scalar)
    assert res_scalar.cleaned_intervals == [850.0]

    res_list = cleaner.clean_sample(sample_list)
    assert res_list.cleaned_intervals == [845.0, 855.0]

    res_none = cleaner.clean_sample(sample_none)
    assert res_none.cleaned_intervals == []

    # Sequence aggregation
    res_combined = cleaner.clean_samples([sample_scalar, sample_list, sample_none])
    assert res_combined.cleaned_intervals == [850.0, 845.0, 855.0]
    assert res_combined.valid_count == 3


# =====================================================================
# 6. Chronological ordering
# =====================================================================

def test_window_buffer_preserves_chronological_ordering(base_time):
    """Verify samples inserted out-of-order are sorted chronologically in the buffer."""
    buffer = WindowBuffer(WindowConfig(window_duration_sec=60.0))

    s1 = make_sample(base_time + timedelta(seconds=10), heart_rate=70.0)
    s2 = make_sample(base_time + timedelta(seconds=2), heart_rate=72.0)
    s3 = make_sample(base_time + timedelta(seconds=5), heart_rate=75.0)

    # Insert out of order: 10s, then 2s, then 5s
    buffer.add_sample(s1)
    buffer.add_sample(s2)
    buffer.add_sample(s3)

    samples = buffer.get_samples()
    timestamps = [s.timestamp for s in samples]

    assert timestamps == sorted(timestamps)
    assert [s.heart_rate for s in samples] == [72.0, 75.0, 70.0]


# =====================================================================
# 7. Window insertion
# =====================================================================

def test_window_buffer_insertion_and_counters(base_time):
    """Verify buffer tracks sample counts and timestamps accurately."""
    buffer = WindowBuffer(WindowConfig(window_duration_sec=60.0))

    assert buffer.sample_count == 0
    assert buffer.total_samples_added == 0
    assert buffer.earliest_timestamp is None
    assert buffer.latest_timestamp is None

    s1 = make_sample(base_time)
    s2 = make_sample(base_time + timedelta(seconds=5))
    buffer.add_samples([s1, s2])

    assert buffer.sample_count == 2
    assert buffer.total_samples_added == 2
    assert buffer.earliest_timestamp == base_time
    assert buffer.latest_timestamp == base_time + timedelta(seconds=5)


# =====================================================================
# 8. Samples leaving the rolling window
# =====================================================================

def test_samples_leave_rolling_window_deterministically(base_time):
    """Verify samples older than window_duration_sec are pruned when time advances."""
    config = WindowConfig(window_duration_sec=10.0, auto_prune=True)
    buffer = WindowBuffer(config)

    # Insert sample at t=0s and t=5s
    buffer.add_sample(make_sample(base_time))
    buffer.add_sample(make_sample(base_time + timedelta(seconds=5)))
    assert buffer.sample_count == 2

    # Insert sample at t=12s. Cutoff is 12 - 10 = 2s.
    # Sample at t=0s should be pruned (0 < 2). Sample at 5s is retained (5 >= 2).
    buffer.add_sample(make_sample(base_time + timedelta(seconds=12)))

    assert buffer.sample_count == 2
    assert buffer.total_samples_pruned == 1
    assert buffer.earliest_timestamp == base_time + timedelta(seconds=5)
    assert buffer.latest_timestamp == base_time + timedelta(seconds=12)


def test_manual_prune_without_auto_prune(base_time):
    """Verify manual pruning works when auto_prune is disabled."""
    config = WindowConfig(window_duration_sec=10.0, auto_prune=False)
    buffer = WindowBuffer(config)

    buffer.add_sample(make_sample(base_time))
    buffer.add_sample(make_sample(base_time + timedelta(seconds=15)))

    # Both present because auto_prune is False
    assert buffer.sample_count == 2

    # Prune manually
    pruned = buffer.prune()
    assert pruned == 1
    assert buffer.sample_count == 1
    assert buffer.earliest_timestamp == base_time + timedelta(seconds=15)


# =====================================================================
# 9. Configurable window duration
# =====================================================================

@pytest.mark.parametrize("duration_sec", [15.0, 30.0, 60.0, 120.0])
def test_configurable_window_duration(base_time, duration_sec):
    """Verify buffer obeys different configured window durations."""
    config = WindowConfig(window_duration_sec=duration_sec)
    buffer = WindowBuffer(config)

    # Insert sample at t=0 and t=duration_sec + 1
    buffer.add_sample(make_sample(base_time))
    buffer.add_sample(make_sample(base_time + timedelta(seconds=duration_sec + 1)))

    # First sample should have been pruned
    assert buffer.sample_count == 1
    assert buffer.total_samples_pruned == 1
    assert buffer.earliest_timestamp == base_time + timedelta(seconds=duration_sec + 1)


# =====================================================================
# 10. Configurable step
# =====================================================================

def test_configurable_step_behavior(base_time):
    """Verify can_step and step enforce the configured step_sec progression."""
    config = WindowConfig(window_duration_sec=30.0, step_sec=5.0, min_samples_required=2)
    buffer = WindowBuffer(config)

    # Buffer with 1 sample cannot step (not ready)
    buffer.add_sample(make_sample(base_time))
    assert not buffer.can_step()
    assert buffer.step() is None

    # Buffer with 2 samples at t=1s can step initially
    buffer.add_sample(make_sample(base_time + timedelta(seconds=1)))
    assert buffer.can_step()

    snapshot1 = buffer.step()
    assert snapshot1 is not None
    assert snapshot1.sample_count == 2

    # Immediately afterwards, cannot step again because 0 seconds elapsed since step
    assert not buffer.can_step()
    assert buffer.step() is None

    # Advance by 4 seconds (total 5s from base_time, but only 4s since step at t=1s)
    buffer.add_sample(make_sample(base_time + timedelta(seconds=5)))
    assert not buffer.can_step()  # 5 - 1 = 4s < 5s step

    # Advance by 6 seconds from base_time (5s since t=1s)
    buffer.add_sample(make_sample(base_time + timedelta(seconds=6)))
    assert buffer.can_step()  # 6 - 1 = 5s >= 5s step

    snapshot2 = buffer.step()
    assert snapshot2 is not None
    assert snapshot2.sample_count == 4


def test_slide_windows_offline(base_time):
    """Verify offline sliding window generator produces correct stepped windows."""
    config = WindowConfig(window_duration_sec=10.0, step_sec=5.0, min_samples_required=3)

    # 15 samples at 1 Hz (0s to 14s)
    samples = [make_sample(base_time + timedelta(seconds=i)) for i in range(15)]

    windows = slide_windows(samples, config)

    assert len(windows) > 0
    for win in windows:
        assert win.sample_count >= 3
        assert win.duration_sec <= 10.0


# =====================================================================
# 11. Irregular timestamps and gaps
# =====================================================================

def test_irregular_timestamps_and_gap_detection(base_time):
    """Verify buffer handles irregular sampling rates and identifies telemetry gaps without fabricating data."""
    buffer = WindowBuffer(WindowConfig(window_duration_sec=60.0))

    # Irregular intervals: 0.0s, 0.7s, 2.1s, 25.0s (gap of 22.9s!), 26.0s
    t_offsets = [0.0, 0.7, 2.1, 25.0, 26.0]
    for off in t_offsets:
        buffer.add_sample(make_sample(base_time + timedelta(seconds=off)))

    assert buffer.sample_count == 5
    # Max gap should be (25.0 - 2.1) = 22.9 seconds
    assert pytest.approx(buffer.get_max_gap_sec(), 0.01) == 22.9

    # Gaps exceeding 5 seconds
    gaps = buffer.get_gaps(threshold_sec=5.0)
    assert len(gaps) == 1
    prev_t, next_t, gap_sec = gaps[0]
    assert prev_t == base_time + timedelta(seconds=2.1)
    assert next_t == base_time + timedelta(seconds=25.0)
    assert pytest.approx(gap_sec, 0.01) == 22.9

    # No synthetic samples were created
    assert [s.timestamp for s in buffer.get_samples()] == [base_time + timedelta(seconds=off) for off in t_offsets]


# =====================================================================
# 12. Empty and insufficient windows
# =====================================================================

def test_empty_window_state():
    """Verify behavior of completely empty WindowBuffer."""
    buffer = WindowBuffer()

    assert buffer.is_empty()
    assert not buffer.is_ready()
    assert buffer.status() == "EMPTY"
    assert buffer.get_samples() == []
    assert buffer.get_time_span_sec() == 0.0
    assert buffer.get_all_rr_intervals() == []
    assert buffer.get_all_heart_rates() == []
    assert buffer.snapshot() is None
    assert buffer.step() is None


def test_insufficient_samples_state(base_time):
    """Verify buffer detects insufficient sample count."""
    config = WindowConfig(min_samples_required=5)
    buffer = WindowBuffer(config)

    buffer.add_samples([make_sample(base_time + timedelta(seconds=i)) for i in range(3)])

    assert not buffer.is_empty()
    assert not buffer.is_ready()
    assert buffer.status() == "INSUFFICIENT_SAMPLES"


def test_insufficient_duration_state(base_time):
    """Verify buffer detects insufficient elapsed duration even if sample count is met."""
    config = WindowConfig(min_samples_required=3, min_duration_sec=10.0)
    buffer = WindowBuffer(config)

    # 5 samples arrive within 2 seconds
    buffer.add_samples([make_sample(base_time + timedelta(seconds=i * 0.5)) for i in range(5)])

    assert buffer.sample_count == 5  # >= min_samples_required (3)
    assert buffer.get_time_span_sec() == 2.0  # < min_duration_sec (10.0)
    assert not buffer.is_ready()
    assert buffer.status() == "INSUFFICIENT_DURATION"

    # Now add sample at t=12s
    buffer.add_sample(make_sample(base_time + timedelta(seconds=12.0)))
    assert buffer.get_time_span_sec() == 12.0
    assert buffer.is_ready()
    assert buffer.status() == "READY"


# =====================================================================
# 13. No mutation of original telemetry samples
# =====================================================================

def test_no_mutation_of_telemetry_samples(base_time):
    """Verify TelemetrySample instances are frozen and never mutated by cleaner or buffer."""
    sample = make_sample(base_time, heart_rate=80.0, rr_interval=[750.0])

    # 1. Pydantic model is frozen
    with pytest.raises((ValidationError, TypeError)):
        sample.heart_rate = 90.0  # type: ignore

    # 2. cleaner does not mutate sample
    cleaner = RRCleaner()
    res = cleaner.clean_sample(sample)
    assert sample.heart_rate == 80.0
    assert sample.rr_interval == [750.0]

    # 3. buffer does not mutate sample
    buffer = WindowBuffer()
    buffer.add_sample(sample)
    retrieved = buffer.get_samples()[0]
    assert retrieved.heart_rate == 80.0
    assert retrieved.rr_interval == [750.0]

    # 4. mutating buffer returned list does not affect buffer internal state
    samples_list = buffer.get_samples()
    samples_list.clear()
    assert buffer.sample_count == 1
