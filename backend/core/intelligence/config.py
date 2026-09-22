"""Configuration models for AeroVital Intelligence & State Estimation.

Defines EstimatorConfig: centralized repository for all prototype engineering
thresholds and operational phase classifications.

IMPORTANT: All thresholds represent UNVALIDATED PROTOTYPE ENGINEERING PARAMETERS
for testing the intelligence pipeline. None represent medically, clinically,
physiologically, or aviation-certified thresholds.
"""

from typing import Set
from pydantic import BaseModel, ConfigDict, Field

from backend.core.schemas.context import MissionPhase


class EstimatorConfig(BaseModel):
    """Configurable engineering placeholders for Step 7 state estimation.
    
    IMPORTANT: All parameters below represent UNVALIDATED PROTOTYPE ENGINEERING PARAMETERS
    for testing the intelligence pipeline. None represent medically, clinically, 
    physiologically, or aviation-certified thresholds.
    """
    model_config = ConfigDict(frozen=True)

    # Workload Gating Placeholders
    g_load_workload_threshold: float = Field(
        default=1.5,
        gt=0.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: G-load threshold for maneuver workload."
    )
    g_load_nominal_max: float = Field(
        default=1.2,
        gt=0.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Maximum G-load considered unexceptional/benign."
    )
    activity_workload_threshold: float = Field(
        default=0.30,
        gt=0.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Dynamic activity threshold for somatic workload."
    )
    
    # Physiological Delta Placeholders
    hr_deviation_workload_threshold: float = Field(
        default=10.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Delta HR (BPM) threshold for workload activation."
    )
    hr_deviation_nominal_max: float = Field(
        default=10.0,
        gt=0.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Maximum absolute HR delta (BPM) for normal concordance."
    )
    rmssd_ratio_fatigue_threshold: float = Field(
        default=0.70,
        gt=0.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: RMSSD ratio cutoff for autonomic depression."
    )
    rmssd_ratio_nominal_min: float = Field(
        default=0.85,
        gt=0.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Minimum RMSSD ratio for positive normal confirmation."
    )
    
    # Quality Screening Placeholder
    motion_corruption_threshold: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Quality index above which sensor readings are marked contaminated."
    )

    # Phase Groupings (Prototypes)
    high_workload_phases: Set[MissionPhase] = Field(
        default_factory=lambda: {
            MissionPhase.TAKEOFF,
            MissionPhase.CLIMB,
            MissionPhase.COMBAT_MANEUVER,
            MissionPhase.HIGH_G,
            MissionPhase.APPROACH,
            MissionPhase.LANDING,
            MissionPhase.EMERGENCY,
        },
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Flight phases categorized as high operational workload."
    )
    benign_phases: Set[MissionPhase] = Field(
        default_factory=lambda: {
            MissionPhase.CRUISE,
            MissionPhase.TAXI,
            MissionPhase.PRE_FLIGHT,
            MissionPhase.POST_FLIGHT,
        },
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Flight phases categorized as low/unexceptional workload."
    )
