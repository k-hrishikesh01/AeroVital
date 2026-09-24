"""Descriptive Feature Extraction Engine for AeroVital Core.

Computes descriptive mathematical metrics over temporal observation windows:
- HRV Features: mean RR, SDNN, RMSSD, pNN50, valid intervals count.
- Heart Rate Dynamics: mean HR, min HR, max HR, sample HR std, HR range, OLS HR trend.
- Motion Features: acceleration magnitude, variance, peak magnitude, activity intensity.

STRICT PRINCIPLES:
1. Operational minimums configured in FeatureConfig override mathematical minimums.
2. RMSSD and pNN50 evaluate differences strictly over genuinely consecutive adjacent beats (j == i + 1).
   Never calculates a difference across a rejected artifact gap.
3. Accelerometer contract: AccelUnit.G uses 1.0, AccelUnit.M_S2 uses 9.80665, AccelUnit.UNSPECIFIED returns None.
   Zero unit guessing and zero median fallbacks.
4. Baseline comparison features remain strictly default/unavailable (computed in Step 6).
5. Zero fatigue scoring, zero fatigue weights, zero clinical claims, zero ML models.
6. Zero mutation of input samples, buffers, or raw interval sequences.
"""

from datetime import datetime, timezone
import math
from typing import List, Optional, Sequence, Tuple

from backend.core.quality.rules import AccelUnit
from backend.core.schemas.features import (
    BaselineComparisonFeatures,
    FeatureVector,
    HeartRateFeatures,
    HRVFeatures,
    MotionFeatures,
)
from backend.core.schemas.telemetry import TelemetrySample
from backend.core.preprocessing.cleaner import RRCleaner, RRCleaningResult
from backend.core.preprocessing.windowing import WindowSnapshot
from backend.core.features.config import FeatureConfig, HRTrendUnit


class FeatureExtractor:
    """Deterministic extractor of descriptive summary metrics over temporal windows."""

    def __init__(
        self,
        config: Optional[FeatureConfig] = None,
        cleaner: Optional[RRCleaner] = None,
    ):
        self.config = config or FeatureConfig()
        self.cleaner = cleaner or RRCleaner()

    def extract_features(self, snapshot: WindowSnapshot) -> FeatureVector:
        """Extract all feature groups from an evaluated WindowSnapshot.
        
        Args:
            snapshot: WindowSnapshot containing chronological TelemetrySamples.
            
        Returns:
            FeatureVector with populated descriptive features.
        """
        return self.extract_from_samples(
            samples=snapshot.samples,
            window_start=snapshot.window_start,
            window_end=snapshot.window_end,
        )

    def extract_from_samples(
        self,
        samples: Sequence[TelemetrySample],
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
    ) -> FeatureVector:
        """Extract all feature groups from a sequence of TelemetrySamples.
        
        Args:
            samples: Ordered sequence of TelemetrySamples.
            window_start: Optional explicit window start timestamp.
            window_end: Optional explicit window end timestamp.
            
        Returns:
            FeatureVector with populated descriptive features.
        """
        # 1. Determine window boundaries without mutating input
        if not samples:
            now = datetime.now(timezone.utc)
            start_ts = window_start or now
            end_ts = window_end or now
        else:
            start_ts = window_start or min(s.timestamp for s in samples)
            end_ts = window_end or max(s.timestamp for s in samples)

        duration_sec = max(0.0, (end_ts - start_ts).total_seconds())

        # 2. Extract each descriptive group
        hr_features = self._extract_hr_features(samples)
        hrv_features = self._extract_hrv_features(samples)
        motion_features = self._extract_motion_features(samples)

        # 3. Baseline comparison remains explicitly unavailable in Layer A
        baseline_features = BaselineComparisonFeatures(
            baseline_available=False,
            hr_deviation_from_baseline=None,
            hrv_rmssd_ratio_to_baseline=None,
        )

        return FeatureVector(
            window_start=start_ts,
            window_end=end_ts,
            window_duration_sec=duration_sec,
            hr_features=hr_features,
            hrv_features=hrv_features,
            motion_features=motion_features,
            baseline_features=baseline_features,
        )

    # =========================================================================
    # Group 1: HRV Features (Artifact-Suppressed Inter-Beat Intervals)
    # =========================================================================

    def _extract_hrv_features(self, samples: Sequence[TelemetrySample]) -> HRVFeatures:
        """Extract time-domain HRV features from artifact-suppressed RR intervals.
        
        Ensures RMSSD and pNN50 compute differences strictly across genuinely
        consecutive beats (original index j == i + 1).
        """
        # Clean all RR intervals from the samples while preserving original index provenance
        cleaning_res: RRCleaningResult = self.cleaner.clean_samples(samples)
        clean_rr = cleaning_res.cleaned_intervals
        retained_idx = cleaning_res.retained_indices
        n_clean = len(clean_rr)

        # Count of clean intervals is always reported faithfully
        if n_clean < self.config.min_rr_samples_for_hrv:
            return HRVFeatures(
                mean_rr_ms=None,
                sdnn_ms=None,
                rmssd_ms=None,
                pnn50_percent=None,
                valid_intervals_count=n_clean,
            )

        # 1. Mean RR
        mean_rr = sum(clean_rr) / n_clean

        # 2. SDNN (Sample standard deviation with Bessel's correction N - 1)
        var_rr = sum((rr - mean_rr) ** 2 for rr in clean_rr) / (n_clean - 1)
        sdnn = math.sqrt(var_rr)

        # 3. RMSSD & pNN50: Strictly consecutive adjacent pairs (retained_idx[k+1] == retained_idx[k] + 1)
        consecutive_diffs: List[float] = []
        for k in range(n_clean - 1):
            if retained_idx[k + 1] == retained_idx[k] + 1:
                consecutive_diffs.append(clean_rr[k + 1] - clean_rr[k])

        p_pairs = len(consecutive_diffs)
        if p_pairs < self.config.min_consecutive_rr_pairs:
            rmssd = None
            pnn50 = None
        else:
            sum_sq_diff = sum(d ** 2 for d in consecutive_diffs)
            rmssd = math.sqrt(sum_sq_diff / p_pairs)

            nn50_count = sum(1 for d in consecutive_diffs if abs(d) > 50.0)
            pnn50 = (nn50_count / p_pairs) * 100.0

        return HRVFeatures(
            mean_rr_ms=mean_rr,
            sdnn_ms=sdnn,
            rmssd_ms=rmssd,
            pnn50_percent=pnn50,
            valid_intervals_count=n_clean,
        )

    # =========================================================================
    # Group 2: Heart Rate Dynamics
    # =========================================================================

    def _extract_hr_features(self, samples: Sequence[TelemetrySample]) -> HeartRateFeatures:
        """Extract descriptive heart rate metrics and linear trend slope."""
        hr_points: List[Tuple[datetime, float]] = []
        for s in samples:
            if s.heart_rate is not None and not math.isnan(s.heart_rate) and not math.isinf(s.heart_rate):
                hr_points.append((s.timestamp, float(s.heart_rate)))

        m_samples = len(hr_points)
        if m_samples < self.config.min_hr_samples_for_dynamics:
            return HeartRateFeatures(
                mean_hr=None,
                min_hr=None,
                max_hr=None,
                hr_std=None,
                hr_range=None,
                hr_trend=None,
            )

        hr_vals = [pt[1] for pt in hr_points]
        mean_hr = sum(hr_vals) / m_samples
        min_hr = min(hr_vals)
        max_hr = max(hr_vals)
        hr_range = max_hr - min_hr

        # Sample standard deviation (Bessel's correction M - 1)
        var_hr = sum((hr - mean_hr) ** 2 for hr in hr_vals) / (m_samples - 1)
        hr_std = math.sqrt(var_hr)

        # OLS Linear Trend Slope over elapsed seconds
        t0 = hr_points[0][0]
        t_seconds = [(pt[0] - t0).total_seconds() for pt in hr_points]
        mean_t = sum(t_seconds) / m_samples

        numerator = sum((t_seconds[i] - mean_t) * (hr_vals[i] - mean_hr) for i in range(m_samples))
        denominator = sum((t_seconds[i] - mean_t) ** 2 for i in range(m_samples))

        if denominator <= 0.0:
            hr_trend = None
        else:
            raw_slope_per_sec = numerator / denominator
            if self.config.hr_trend_unit == HRTrendUnit.BPM_PER_MINUTE:
                hr_trend = raw_slope_per_sec * 60.0
            else:
                hr_trend = raw_slope_per_sec

        return HeartRateFeatures(
            mean_hr=mean_hr,
            min_hr=min_hr,
            max_hr=max_hr,
            hr_std=hr_std,
            hr_range=hr_range,
            hr_trend=hr_trend,
        )

    # =========================================================================
    # Group 3: Motion Features (Inertial Dynamics)
    # =========================================================================

    def _extract_motion_features(self, samples: Sequence[TelemetrySample]) -> MotionFeatures:
        """Extract 3-axis accelerometer descriptive metrics and activity intensity."""
        valid_triplets: List[Tuple[float, float, float]] = []
        for s in samples:
            if (
                s.has_acceleration()
                and not math.isnan(s.accel_x) and not math.isinf(s.accel_x)  # type: ignore
                and not math.isnan(s.accel_y) and not math.isinf(s.accel_y)  # type: ignore
                and not math.isnan(s.accel_z) and not math.isinf(s.accel_z)  # type: ignore
            ):
                valid_triplets.append((float(s.accel_x), float(s.accel_y), float(s.accel_z)))  # type: ignore

        k_samples = len(valid_triplets)
        if k_samples < self.config.min_accel_samples_for_motion:
            return MotionFeatures(
                mean_magnitude=None,
                variance_magnitude=None,
                peak_magnitude=None,
                activity_intensity=None,
            )

        magnitudes = [math.sqrt(ax ** 2 + ay ** 2 + az ** 2) for ax, ay, az in valid_triplets]
        mean_mag = sum(magnitudes) / k_samples
        peak_mag = max(magnitudes)

        # Sample variance with Bessel's correction (K - 1)
        var_mag = sum((m - mean_mag) ** 2 for m in magnitudes) / (k_samples - 1)

        # Activity Intensity with Strict Unit Contract
        if self.config.accel_unit == AccelUnit.G:
            gravity_ref = 1.0
            activity_intensity = sum(abs(m - gravity_ref) for m in magnitudes) / k_samples
        elif self.config.accel_unit == AccelUnit.M_S2:
            gravity_ref = 9.80665
            activity_intensity = sum(abs(m - gravity_ref) for m in magnitudes) / k_samples
        else:
            # AccelUnit.UNSPECIFIED: strict contract requires returning None (no guessing, no median)
            activity_intensity = None

        return MotionFeatures(
            mean_magnitude=mean_mag,
            variance_magnitude=var_mag,
            peak_magnitude=peak_mag,
            activity_intensity=activity_intensity,
        )
