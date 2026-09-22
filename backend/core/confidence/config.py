"""Configuration models for AeroVital Confidence Evaluation & Result Generation.

Defines ConfidenceConfig: centralized parameters, weights, and thresholds
for Step 8 evidence-confidence calculation and abstention gating.

IMPORTANT: All thresholds and weights represent UNVALIDATED PROTOTYPE ENGINEERING PARAMETERS
for testing the pipeline. None represent medically, clinically, physiologically,
or aviation-certified thresholds.
"""

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceConfig(BaseModel):
    """Configurable engineering parameters for Step 8 confidence and result generation.
    
    IMPORTANT: All parameters below represent UNVALIDATED PROTOTYPE ENGINEERING PARAMETERS
    for testing the intelligence pipeline. None represent medically, clinically, 
    physiologically, or aviation-certified thresholds.
    """
    model_config = ConfigDict(frozen=True)

    # Estimator metadata provenance
    estimator_id: str = Field(
        default="AeroVitalConfidenceEvaluator-v1.0",
        description="Identifier of the Step 8 confidence and result evaluator."
    )
    disclaimer: str = Field(
        default="Provisional prototype estimator for pipeline testing only; not clinically or operationally validated.",
        description="Mandatory warning disclaimer accompanying any provisional evaluation."
    )

    # Abstention Gating Thresholds
    min_overall_sqi: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Minimum overall SQI required to pass global telemetry quality gate."
    )
    confidence_threshold: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Minimum confidence C(t) required to retain candidate state without abstention."
    )

    # Quality Gate Penalty Placeholders
    unacceptable_telemetry_cap: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Maximum global SQI score component when telemetry is unacceptable."
    )

    # Confidence Dimension Weights (must sum to 1.0)
    weight_global_sqi: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Weight of global telemetry SQI in confidence synthesis."
    )
    weight_channel_quality: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Weight of relied-upon channel quality in confidence synthesis."
    )
    weight_evidence_completeness: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Weight of candidate evidence completeness in confidence synthesis."
    )
    weight_motion_integrity: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Weight of motion artifact freedom in confidence synthesis."
    )

    # Explanatory factor limit
    max_dominant_factors: int = Field(
        default=3,
        ge=1,
        le=10,
        description="UNVALIDATED PROTOTYPE ENGINEERING PARAMETER: Maximum number of dominant factors to preserve in final result."
    )
