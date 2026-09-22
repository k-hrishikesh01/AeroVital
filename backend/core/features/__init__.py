"""Feature Extraction Layer for AeroVital Core.

Provides:
- FeatureConfig, HRTrendUnit: Extraction parameter and unit configuration.
- FeatureExtractor: Descriptive statistical feature extraction over temporal windows.
"""

from backend.core.features.config import FeatureConfig, HRTrendUnit
from backend.core.features.extractor import FeatureExtractor

__all__ = [
    "FeatureConfig",
    "HRTrendUnit",
    "FeatureExtractor",
]
