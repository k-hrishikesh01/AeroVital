"""Top-Level Core Pipeline Layer for AeroVital.

Provides AeroVitalPipeline: framework-independent orchestrator connecting
Validation, Quality, Windowing, Features, Baseline, Intelligence, and Confidence.
"""

from backend.core.pipeline.pipeline import AeroVitalPipeline

__all__ = [
    "AeroVitalPipeline",
]
