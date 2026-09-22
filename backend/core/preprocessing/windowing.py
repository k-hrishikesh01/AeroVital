"""Temporal Windowing and Rolling Buffer for AeroVital Core.

Provides deterministic temporal aggregation of incoming TelemetrySamples:
- WindowConfig: Centralized configurable window duration, step, and sufficiency parameters.
- WindowBuffer: Rolling buffer that preserves chronological ordering, deterministically prunes expired samples,
  and handles irregular sample intervals and gaps without data fabrication.
- WindowSnapshot: Immutable representation of an evaluated temporal window.
- slice_windows: Offline/batch sliding window generator across historical telemetry sequences.

IMPORTANT: All parameters represent configurable prototype engineering placeholders;
none represent clinically, empirically, or operationally validated cutoffs.
"""

import bisect
from datetime import datetime, timedelta
from typing import Any, List, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field

from backend.core.schemas.telemetry import TelemetrySample


class WindowConfig(BaseModel):
    """Configuration for temporal windowing and rolling buffers.
    
    IMPORTANT: All parameters below represent configurable prototype engineering
    placeholders. None represent clinically, empirically, or operationally validated limits.
    """
    model_config = ConfigDict(frozen=True)

    window_duration_sec: float = Field(
        default=60.0,
        gt=0.0,
        description="Temporal duration of the active window in seconds. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    step_sec: float = Field(
        default=1.0,
        gt=0.0,
        description="Slide/advance step in seconds for window progression. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    min_samples_required: int = Field(
        default=5,
        ge=1,
        description="Minimum number of samples required for window sufficiency. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    min_duration_sec: Optional[float] = Field(
        default=None,
        description="Optional minimum elapsed time span (latest_ts - earliest_ts in seconds) required for window sufficiency. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    auto_prune: bool = Field(
        default=True,
        description="Whether to automatically prune expired samples on sample insertion. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )


class WindowSnapshot(BaseModel):
    """Immutable snapshot of a window at a specific point in time."""
    model_config = ConfigDict(frozen=True)

    window_start: datetime = Field(..., description="Timestamp of the earliest sample or window boundary.")
    window_end: datetime = Field(..., description="Timestamp of the latest sample or window boundary.")
    samples: List[TelemetrySample] = Field(..., description="Chronologically ordered TelemetrySamples within this window.")

    @property
    def sample_count(self) -> int:
        """Count of samples contained within this window."""
        return len(self.samples)

    @property
    def duration_sec(self) -> float:
        """Elapsed time spanned by the window in seconds."""
        return (self.window_end - self.window_start).total_seconds()

    def get_all_rr_intervals(self) -> List[float]:
        """Collect all RR intervals across all samples in the window chronologically."""
        intervals: List[float] = []
        for sample in self.samples:
            intervals.extend(sample.get_rr_intervals())
        return intervals

    def get_all_heart_rates(self) -> List[float]:
        """Collect all non-null heart rate readings in the window chronologically."""
        return [s.heart_rate for s in self.samples if s.heart_rate is not None]


class WindowBuffer:
    """Rolling temporal buffer for TelemetrySamples.
    
    Guarantees:
    - Chronological sorting: Samples are always maintained in ascending timestamp order.
    - Deterministic pruning: Samples older than (latest_timestamp - window_duration_sec) are removed.
    - No data fabrication: Missing periods, irregular intervals, and gaps are preserved without synthetic points.
    - Immutability: Original TelemetrySamples are never mutated.
    """

    def __init__(self, config: Optional[WindowConfig] = None):
        self.config = config or WindowConfig()
        self._samples: List[TelemetrySample] = []
        self._total_samples_added: int = 0
        self._total_samples_pruned: int = 0
        self._last_step_time: Optional[datetime] = None

    @property
    def sample_count(self) -> int:
        """Current number of active samples in the buffer."""
        return len(self._samples)

    @property
    def total_samples_added(self) -> int:
        """Total lifetime samples received by this buffer."""
        return self._total_samples_added

    @property
    def total_samples_pruned(self) -> int:
        """Total lifetime samples pruned from this buffer."""
        return self._total_samples_pruned

    @property
    def earliest_timestamp(self) -> Optional[datetime]:
        """Timestamp of the oldest active sample in the buffer, or None if empty."""
        return self._samples[0].timestamp if self._samples else None

    @property
    def latest_timestamp(self) -> Optional[datetime]:
        """Timestamp of the newest active sample in the buffer, or None if empty."""
        return self._samples[-1].timestamp if self._samples else None

    def add_sample(self, sample: TelemetrySample) -> None:
        """Insert a sample into the buffer, maintaining chronological order and pruning expired samples.
        
        Args:
            sample: Validated TelemetrySample.
        """
        # Maintain chronological ordering via sorted insertion
        if not self._samples or sample.timestamp >= self._samples[-1].timestamp:
            self._samples.append(sample)
        elif sample.timestamp < self._samples[0].timestamp:
            self._samples.insert(0, sample)
        else:
            # Binary search insertion to keep strictly sorted
            bisect.insort(self._samples, sample, key=lambda s: s.timestamp)

        self._total_samples_added += 1

        if self.config.auto_prune:
            self.prune()

    def add_samples(self, samples: Sequence[TelemetrySample]) -> None:
        """Batch insert multiple TelemetrySamples.
        
        Args:
            samples: Sequence of TelemetrySamples.
        """
        for sample in samples:
            self.add_sample(sample)

    def prune(self, cutoff_timestamp: Optional[datetime] = None) -> int:
        """Prune samples strictly older than the cutoff timestamp.
        
        If cutoff_timestamp is None, it is calculated as:
        latest_timestamp - timedelta(seconds=self.config.window_duration_sec).
        
        Returns:
            Number of samples pruned in this call.
        """
        if not self._samples:
            return 0

        if cutoff_timestamp is None:
            latest = self._samples[-1].timestamp
            cutoff = latest - timedelta(seconds=self.config.window_duration_sec)
        else:
            cutoff = cutoff_timestamp

        # Find cutoff index: all samples with timestamp < cutoff are pruned
        prune_count = 0
        for s in self._samples:
            if s.timestamp < cutoff:
                prune_count += 1
            else:
                break

        if prune_count > 0:
            self._samples = self._samples[prune_count:]
            self._total_samples_pruned += prune_count

        return prune_count

    def get_samples(self) -> List[TelemetrySample]:
        """Return a shallow copy of active TelemetrySamples in chronological order."""
        return list(self._samples)

    def get_time_span_sec(self) -> float:
        """Calculate the elapsed time span in seconds between earliest and latest active samples.
        
        Returns 0.0 if fewer than 2 samples are in the buffer.
        """
        if len(self._samples) < 2:
            return 0.0
        return (self._samples[-1].timestamp - self._samples[0].timestamp).total_seconds()

    def is_empty(self) -> bool:
        """Check whether the buffer has zero samples."""
        return len(self._samples) == 0

    def is_ready(self) -> bool:
        """Check whether the buffer contains sufficient data to form a valid window."""
        if len(self._samples) < self.config.min_samples_required:
            return False

        if self.config.min_duration_sec is not None:
            if self.get_time_span_sec() < self.config.min_duration_sec:
                return False

        return True

    def status(self) -> str:
        """Return a descriptive readiness status for the active buffer."""
        if len(self._samples) == 0:
            return "EMPTY"
        if len(self._samples) < self.config.min_samples_required:
            return "INSUFFICIENT_SAMPLES"
        if self.config.min_duration_sec is not None and self.get_time_span_sec() < self.config.min_duration_sec:
            return "INSUFFICIENT_DURATION"
        return "READY"

    def get_all_rr_intervals(self) -> List[float]:
        """Collect all RR intervals across active samples in chronological order."""
        intervals: List[float] = []
        for sample in self._samples:
            intervals.extend(sample.get_rr_intervals())
        return intervals

    def get_all_heart_rates(self) -> List[float]:
        """Collect all non-null heart rate readings across active samples in chronological order."""
        return [s.heart_rate for s in self._samples if s.heart_rate is not None]

    def get_gaps(self, threshold_sec: float) -> List[Tuple[datetime, datetime, float]]:
        """Identify temporal gaps between consecutive samples exceeding threshold_sec.
        
        Args:
            threshold_sec: Minimum gap duration in seconds to report.
            
        Returns:
            List of tuples: (prior_timestamp, next_timestamp, gap_duration_sec).
        """
        gaps: List[Tuple[datetime, datetime, float]] = []
        if len(self._samples) < 2:
            return gaps

        for i in range(1, len(self._samples)):
            gap = (self._samples[i].timestamp - self._samples[i - 1].timestamp).total_seconds()
            if gap > threshold_sec:
                gaps.append((self._samples[i - 1].timestamp, self._samples[i].timestamp, gap))

        return gaps

    def get_max_gap_sec(self) -> float:
        """Return the maximum duration in seconds between consecutive samples in the buffer."""
        if len(self._samples) < 2:
            return 0.0
        max_gap = 0.0
        for i in range(1, len(self._samples)):
            gap = (self._samples[i].timestamp - self._samples[i - 1].timestamp).total_seconds()
            if gap > max_gap:
                max_gap = gap
        return max_gap

    def can_step(self) -> bool:
        """Check whether enough time has elapsed since the last step to emit a new window."""
        if not self.is_ready():
            return False

        if self._last_step_time is None:
            return True

        latest = self.latest_timestamp
        if latest is None:
            return False

        elapsed = (latest - self._last_step_time).total_seconds()
        return elapsed >= self.config.step_sec

    def step(self) -> Optional[WindowSnapshot]:
        """Attempt to step the window forward and produce a WindowSnapshot.
        
        Returns:
            WindowSnapshot if can_step() is True, else None.
        """
        if not self.can_step():
            return None

        self._last_step_time = self.latest_timestamp
        return self.snapshot()

    def snapshot(self) -> Optional[WindowSnapshot]:
        """Create an immutable WindowSnapshot of the current active buffer.
        
        Returns:
            WindowSnapshot if buffer is non-empty, else None.
        """
        if not self._samples:
            return None

        return WindowSnapshot(
            window_start=self._samples[0].timestamp,
            window_end=self._samples[-1].timestamp,
            samples=list(self._samples),
        )

    def clear(self) -> None:
        """Reset the buffer, clearing all samples and stepping markers."""
        self._samples.clear()
        self._last_step_time = None
        # Note: lifetime total counters are preserved for auditability


def slide_windows(
    samples: Sequence[TelemetrySample],
    config: Optional[WindowConfig] = None,
) -> List[WindowSnapshot]:
    """Offline sliding window generator across a sequence of TelemetrySamples.
    
    Extracts successive windows of duration config.window_duration_sec,
    advancing by config.step_sec.
    
    Args:
        samples: Sequence of TelemetrySamples (will be sorted chronologically).
        config: WindowConfig with window_duration_sec, step_sec, and min_samples_required.
        
    Returns:
        List of ready WindowSnapshots.
    """
    cfg = config or WindowConfig()
    if not samples:
        return []

    # Sort samples chronologically without mutating input
    sorted_samples = sorted(samples, key=lambda s: s.timestamp)
    total_samples = len(sorted_samples)

    start_time = sorted_samples[0].timestamp
    end_time = sorted_samples[-1].timestamp
    total_span = (end_time - start_time).total_seconds()

    if total_span < 0:
        return []

    windows: List[WindowSnapshot] = []
    window_duration = timedelta(seconds=cfg.window_duration_sec)
    step = timedelta(seconds=cfg.step_sec)

    current_window_start = start_time

    while current_window_start <= end_time:
        current_window_end = current_window_start + window_duration

        # Filter samples that fall in [current_window_start, current_window_end]
        window_samples = [
            s for s in sorted_samples
            if current_window_start <= s.timestamp <= current_window_end
        ]

        # Check sufficiency
        is_sufficient = len(window_samples) >= cfg.min_samples_required
        if is_sufficient and cfg.min_duration_sec is not None:
            if len(window_samples) >= 2:
                span = (window_samples[-1].timestamp - window_samples[0].timestamp).total_seconds()
                if span < cfg.min_duration_sec:
                    is_sufficient = False
            else:
                is_sufficient = False

        if is_sufficient:
            windows.append(WindowSnapshot(
                window_start=window_samples[0].timestamp,
                window_end=window_samples[-1].timestamp,
                samples=window_samples,
            ))

        current_window_start += step

        # Stop if current_window_start exceeds latest timestamp
        if current_window_start > end_time:
            break

    return windows
