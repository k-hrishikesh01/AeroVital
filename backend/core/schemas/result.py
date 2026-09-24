"""Fatigue Estimation Result Schemas for AeroVital.

Provides structured results containing fatigue score, categorical state,
independent confidence, dominant factors, and estimator metadata.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FatigueState(str, Enum):
    """Latent fatigue state categories.
    
    INSUFFICIENT_DATA represents engine abstention when confidence drops below
    the minimum threshold or when essential signals/baselines are missing.
    """
    NORMAL = "NORMAL"
    ELEVATED_WORKLOAD = "ELEVATED_WORKLOAD"
    FATIGUE = "FATIGUE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class EstimationMetadata(BaseModel):
    """Metadata detailing the estimator used and its validation status.
    
    Crucial: Prototype estimators must be explicitly flagged as provisional
    and unvalidated for clinical or operational flight safety decisions.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    estimator_id: str = Field(
        ...,
        description="Identifier of the estimator class/model used."
    )
    is_provisional: bool = Field(
        default=True,
        description="Explicit flag: True indicates a development/testing heuristic, NOT clinically validated."
    )
    disclaimer: str = Field(
        default="Provisional prototype estimator for pipeline testing only; not clinically or operationally validated.",
        description="Mandatory warning disclaimer accompanying any provisional evaluation."
    )
    confidence_threshold_used: float = Field(
        default=0.40,
        description="Engineering placeholder threshold used for abstention gating (NOT a medical cutoff)."
    )
    baseline_version_used: Optional[str] = Field(
        default=None,
        description="Version ID of the PilotBaseline used in this evaluation, if available."
    )


class FatigueEstimationResult(BaseModel):
    """Structured fatigue estimation output returned by the intelligence engine."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: datetime = Field(
        ...,
        description="UTC timestamp of the estimation result."
    )
    fatigue_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Continuous latent fatigue score in [0.0, 1.0]. None if state is INSUFFICIENT_DATA."
    )
    fatigue_state: FatigueState = Field(
        ...,
        description="Discrete fatigue classification."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Independent confidence metric in [0.0, 1.0] reflecting signal quality and data completeness."
    )
    dominant_factors: List[str] = Field(
        default_factory=list,
        description="Top contributing physiological or contextual factors explaining the estimate."
    )
    overall_sqi: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite signal quality index from input telemetry."
    )
    metadata: EstimationMetadata = Field(
        ...,
        description="Estimator provenance and provisional disclaimer metadata."
    )
