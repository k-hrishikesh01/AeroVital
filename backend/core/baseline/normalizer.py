"""Pilot Baseline Normalization for AeroVital Core.

Provides BaselineNormalizer: a stateless, pure transformation service that
computes individual-specific physiological comparisons relative to a pilot's
calibrated baseline profile.

STRICT PRINCIPLES:
1. Pure transformation: input FeatureVector and PilotBaseline are never mutated.
2. Returns a new FeatureVector instance with baseline_features populated.
3. baseline_available=True if and only if a non-null, calibrated (is_calibrated=True)
   PilotBaseline was provided.
4. Independent partial availability: hr_deviation_from_baseline and
   hrv_rmssd_ratio_to_baseline independently evaluate to None when respective operands
   are missing or invalid.
5. Strict numerical safety: protects against division by zero, non-finite (NaN/Inf)
   operands/results, and non-positive baseline values.
6. Zero imputation: no population averages or zero-substitutions.
7. Zero fatigue interpretation: deviations remain purely descriptive comparisons.
"""

import math
from typing import Optional

from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.features import (
    BaselineComparisonFeatures,
    FeatureVector,
)


class BaselineNormalizer:
    """Stateless, deterministic normalizer comparing feature vectors against a pilot baseline."""

    def normalize(
        self,
        features: FeatureVector,
        baseline: Optional[PilotBaseline] = None,
    ) -> FeatureVector:
        """Compare descriptive features against a pilot-specific calibrated baseline.
        
        Args:
            features: Immutable FeatureVector containing descriptive window metrics.
            baseline: Optional calibrated PilotBaseline profile.
            
        Returns:
            A new FeatureVector instance with updated BaselineComparisonFeatures.
        """
        # 1. Check baseline presence and calibration status
        if baseline is None or not baseline.is_calibrated:
            baseline_features = BaselineComparisonFeatures(
                baseline_available=False,
                hr_deviation_from_baseline=None,
                hrv_rmssd_ratio_to_baseline=None,
            )
            return self._build_normalized_vector(features, baseline_features)

        # Baseline is present and calibrated
        baseline_available = True

        # 2. Heart-rate deviation from baseline: mean_hr - resting_heart_rate
        hr_deviation: Optional[float] = None
        mean_hr = features.hr_features.mean_hr
        resting_hr = baseline.resting_heart_rate

        if (
            mean_hr is not None
            and resting_hr is not None
            and isinstance(mean_hr, (int, float))
            and isinstance(resting_hr, (int, float))
            and not math.isnan(mean_hr)
            and not math.isinf(mean_hr)
            and not math.isnan(resting_hr)
            and not math.isinf(resting_hr)
            and resting_hr > 0.0
        ):
            delta = float(mean_hr) - float(resting_hr)
            if not math.isnan(delta) and not math.isinf(delta):
                hr_deviation = delta

        # 3. HRV RMSSD ratio to baseline: rmssd_ms / baseline_rmssd
        rmssd_ratio: Optional[float] = None
        window_rmssd = features.hrv_features.rmssd_ms
        baseline_rmssd = baseline.baseline_rmssd

        if (
            window_rmssd is not None
            and baseline_rmssd is not None
            and isinstance(window_rmssd, (int, float))
            and isinstance(baseline_rmssd, (int, float))
            and not math.isnan(window_rmssd)
            and not math.isinf(window_rmssd)
            and not math.isnan(baseline_rmssd)
            and not math.isinf(baseline_rmssd)
            and baseline_rmssd > 0.0
            and window_rmssd >= 0.0
        ):
            ratio = float(window_rmssd) / float(baseline_rmssd)
            if not math.isnan(ratio) and not math.isinf(ratio):
                rmssd_ratio = ratio

        # 4. Construct updated BaselineComparisonFeatures
        baseline_features = BaselineComparisonFeatures(
            baseline_available=baseline_available,
            hr_deviation_from_baseline=hr_deviation,
            hrv_rmssd_ratio_to_baseline=rmssd_ratio,
        )

        return self._build_normalized_vector(features, baseline_features)

    @staticmethod
    def _build_normalized_vector(
        features: FeatureVector,
        baseline_features: BaselineComparisonFeatures,
    ) -> FeatureVector:
        """Construct a new immutable FeatureVector preserving original descriptive metrics."""
        return FeatureVector(
            window_start=features.window_start,
            window_end=features.window_end,
            window_duration_sec=features.window_duration_sec,
            hr_features=features.hr_features,
            hrv_features=features.hrv_features,
            motion_features=features.motion_features,
            baseline_features=baseline_features,
        )
