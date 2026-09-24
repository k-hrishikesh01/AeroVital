"""Preprocessing and Windowing Layer for AeroVital Core.

Provides:
- RR interval cleaning and artifact suppression (RRCleaner, RRCleaningConfig, RRCleaningResult).
- Temporal rolling buffer and window slicing (WindowBuffer, WindowConfig, WindowSnapshot, slide_windows).
"""

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

__all__ = [
    "RRCleaner",
    "RRCleaningConfig",
    "RRCleaningResult",
    "WindowBuffer",
    "WindowConfig",
    "WindowSnapshot",
    "slide_windows",
]
