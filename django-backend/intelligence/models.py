import uuid
from django.db import models
from django.utils import timezone

from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.result import FatigueEstimationResult, FatigueState


class Baseline(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    pilot = models.ForeignKey(
        "pilots.Pilot",
        on_delete=models.CASCADE,
        related_name="baselines",
    )
    baseline_version = models.CharField(max_length=100, db_index=True)
    resting_heart_rate = models.FloatField()
    baseline_rmssd = models.FloatField(null=True, blank=True)
    baseline_sdnn = models.FloatField(null=True, blank=True)
    baseline_mean_rr = models.FloatField(null=True, blank=True)
    calibration_duration_sec = models.FloatField(null=True, blank=True)
    is_calibrated = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Baseline v{self.baseline_version} for Pilot {self.pilot.pilot_code}"

    def to_core(self) -> PilotBaseline:
        """Convert to verified Core PilotBaseline schema."""
        return PilotBaseline(
            pilot_id=str(self.pilot.id),
            baseline_version=self.baseline_version,
            created_at=self.created_at,
            resting_heart_rate=self.resting_heart_rate,
            baseline_rmssd=self.baseline_rmssd,
            baseline_sdnn=self.baseline_sdnn,
            baseline_mean_rr=self.baseline_mean_rr,
            calibration_duration_sec=self.calibration_duration_sec,
            is_calibrated=self.is_calibrated,
            metadata=self.metadata or {},
        )

    @classmethod
    def from_core(cls, pilot, baseline: PilotBaseline):
        return cls.objects.create(
            pilot=pilot,
            baseline_version=baseline.baseline_version,
            resting_heart_rate=baseline.resting_heart_rate,
            baseline_rmssd=baseline.baseline_rmssd,
            baseline_sdnn=baseline.baseline_sdnn,
            baseline_mean_rr=baseline.baseline_mean_rr,
            calibration_duration_sec=baseline.calibration_duration_sec,
            is_calibrated=baseline.is_calibrated,
            metadata=baseline.metadata,
            created_at=baseline.created_at,
        )


class ModelVersion(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    estimator_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=100)
    is_provisional = models.BooleanField(default=True)
    disclaimer = models.TextField(blank=True)
    confidence_threshold = models.FloatField(default=0.40)
    parameters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.version})"


class StateEstimate(models.Model):
    class StateChoices(models.TextChoices):
        NORMAL = "NORMAL", "Normal"
        ELEVATED_WORKLOAD = "ELEVATED_WORKLOAD", "Elevated Workload"
        FATIGUE = "FATIGUE", "Fatigue"
        INSUFFICIENT_DATA = "INSUFFICIENT_DATA", "Insufficient Data"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    pilot = models.ForeignKey(
        "pilots.Pilot",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="state_estimates",
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="state_estimates",
    )
    feature_window = models.ForeignKey(
        "telemetry.FeatureWindow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="state_estimates",
    )

    timestamp = models.DateTimeField(db_index=True)

    # Core state result fields
    fatigue_state = models.CharField(
        max_length=50,
        choices=StateChoices.choices,
        db_index=True,
    )
    # fatigue_score is None when state is INSUFFICIENT_DATA
    fatigue_score = models.FloatField(null=True, blank=True)
    # Independent confidence metric in [0.0, 1.0]
    confidence = models.FloatField()
    # Composite SQI in [0.0, 1.0]
    overall_sqi = models.FloatField(default=1.0)
    # Contributing factors list
    dominant_factors = models.JSONField(default=list, blank=True)

    # Provenance metadata
    estimator_id = models.CharField(
        max_length=100,
        default="ProvisionalRuleBasedEstimator",
    )
    is_provisional = models.BooleanField(default=True)
    disclaimer = models.TextField(blank=True)
    confidence_threshold_used = models.FloatField(default=0.40)
    baseline_version_used = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    evidence = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        score_repr = f"{self.fatigue_score:.2f}" if self.fatigue_score is not None else "None"
        return f"StateEstimate {self.fatigue_state} (score={score_repr}, conf={self.confidence:.2f}) @ {self.timestamp}"

    @classmethod
    def from_core(
        cls,
        result: FatigueEstimationResult,
        pilot=None,
        mission=None,
        feature_window=None,
        evidence=None,
    ):
        """Create StateEstimate directly from Core FatigueEstimationResult."""
        return cls.objects.create(
            pilot=pilot,
            mission=mission,
            feature_window=feature_window,
            timestamp=result.timestamp,
            fatigue_state=result.fatigue_state.value if hasattr(result.fatigue_state, "value") else str(result.fatigue_state),
            fatigue_score=result.fatigue_score,
            confidence=result.confidence,
            overall_sqi=result.overall_sqi,
            dominant_factors=result.dominant_factors,
            estimator_id=result.metadata.estimator_id,
            is_provisional=result.metadata.is_provisional,
            disclaimer=result.metadata.disclaimer,
            confidence_threshold_used=result.metadata.confidence_threshold_used,
            baseline_version_used=result.metadata.baseline_version_used,
            evidence=evidence or {},
        )