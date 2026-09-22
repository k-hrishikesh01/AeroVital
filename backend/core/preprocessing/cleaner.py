"""RR Interval Preprocessing and Artifact Suppression for AeroVital Core.

Provides deterministic cleaning of inter-beat interval (RR / IBI) observations:
- Detects non-finite values (NaN, Inf).
- Enforces boundary plausibility.
- Identifies and suppresses ectopic intervals and sudden non-physiological deltas.
- Preserves full traceability of retained vs. rejected intervals.
- Never fabricates or imputes missing RR data.

IMPORTANT: All thresholds are configurable prototype engineering placeholders;
none represent clinically, empirically, or operationally validated cutoffs.
"""

import math
from typing import Any, List, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field

from backend.core.schemas.telemetry import TelemetrySample


class RRCleaningConfig(BaseModel):
    """Configurable engineering parameters for RR interval artifact suppression.
    
    IMPORTANT: All parameters below represent configurable prototype engineering
    placeholders. None represent clinically, empirically, or operationally validated limits.
    """
    model_config = ConfigDict(frozen=True)

    min_rr_ms: float = Field(
        default=250.0,
        description="Minimum allowable RR interval in ms (~240 BPM). Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    max_rr_ms: float = Field(
        default=2500.0,
        description="Maximum allowable RR interval in ms (~24 BPM). Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )
    max_successive_diff_ratio: float = Field(
        default=0.40,
        description="Maximum allowable relative jump (|RR_curr - RR_prev| / RR_prev) between successive clean beats. Prototype engineering parameter; not clinically, empirically, or operationally validated."
    )


class RRCleaningResult(BaseModel):
    """Traceable output of an RR interval cleaning operation."""
    model_config = ConfigDict(frozen=True)

    raw_count: int = Field(..., description="Total count of raw RR intervals evaluated.")
    valid_count: int = Field(..., description="Count of valid, retained clean RR intervals.")
    cleaned_intervals: List[float] = Field(..., description="Ordered list of retained clean RR intervals in ms.")
    retained_indices: List[int] = Field(
        default_factory=list,
        description="0-based indices of retained intervals in the original raw sequence."
    )
    rejected_intervals: List[Tuple[Any, str]] = Field(
        default_factory=list,
        description="List of rejected intervals with specific rejection rationale code."
    )

    @property
    def rejection_ratio(self) -> float:
        """Ratio of rejected intervals to raw intervals."""
        if self.raw_count == 0:
            return 0.0
        return len(self.rejected_intervals) / self.raw_count


class RRCleaner:
    """Deterministic artifact suppressor for RR / IBI intervals."""

    def __init__(self, config: Optional[RRCleaningConfig] = None):
        self.config = config or RRCleaningConfig()

    def clean_intervals(self, intervals: Sequence[float]) -> RRCleaningResult:
        """Filter out non-finite, out-of-bounds, or ectopic RR intervals.
        
        Args:
            intervals: Sequence of raw RR intervals in milliseconds.
            
        Returns:
            RRCleaningResult containing clean intervals, original retained indices, and audit log of rejections.
        """
        cleaned: List[float] = []
        retained_indices: List[int] = []
        rejected: List[Tuple[Any, str]] = []

        last_valid: Optional[float] = None

        for idx, rr in enumerate(intervals):
            # 1. Non-finite check
            if not isinstance(rr, (int, float)) or math.isnan(rr) or math.isinf(rr):
                rejected.append((rr, "NON_FINITE"))
                continue

            rr_float = float(rr)

            # 2. Bound plausibility checks
            if rr_float < self.config.min_rr_ms:
                rejected.append((rr_float, "OUT_OF_BOUNDS_LOW"))
                continue

            if rr_float > self.config.max_rr_ms:
                rejected.append((rr_float, "OUT_OF_BOUNDS_HIGH"))
                continue

            # 3. Relative jump check against preceding clean beat
            if last_valid is not None:
                rel_diff = abs(rr_float - last_valid) / last_valid
                if rel_diff > self.config.max_successive_diff_ratio:
                    rejected.append((rr_float, "EXCESSIVE_SUCCESSIVE_DIFF"))
                    continue

            cleaned.append(rr_float)
            retained_indices.append(idx)
            last_valid = rr_float

        return RRCleaningResult(
            raw_count=len(intervals),
            valid_count=len(cleaned),
            cleaned_intervals=cleaned,
            retained_indices=retained_indices,
            rejected_intervals=rejected,
        )

    def clean_sample(self, sample: TelemetrySample) -> RRCleaningResult:
        """Convenience method to clean RR intervals from a TelemetrySample."""
        return self.clean_intervals(sample.get_rr_intervals())

    def clean_samples(self, samples: Sequence[TelemetrySample]) -> RRCleaningResult:
        """Clean all RR intervals aggregated across an ordered sequence of TelemetrySamples.
        
        Extracts RR intervals chronologically without mutating any sample.
        """
        all_intervals: List[float] = []
        for sample in samples:
            all_intervals.extend(sample.get_rr_intervals())
        return self.clean_intervals(all_intervals)
