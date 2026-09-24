import uuid
from django.db import models


class Baseline(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    pilot = models.ForeignKey(
        "pilots.Pilot",
        on_delete=models.CASCADE,
        related_name="baselines"
    )

    metric_name = models.CharField(max_length=100)

    baseline_value = models.FloatField()

    std_deviation = models.FloatField(
        null=True,
        blank=True
    )

    sample_count = models.IntegerField()

    window_duration = models.IntegerField()

    calculated_at = models.DateTimeField()

    valid_from = models.DateTimeField()

    valid_until = models.DateTimeField(
        null=True,
        blank=True
    )

    baseline_version = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.pilot_id} - {self.metric_name}"


class ModelVersion(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(max_length=255)

    version = models.CharField(max_length=100)

    engine_type = models.CharField(max_length=100)

    parameters = models.JSONField(default=dict)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} v{self.version}"


class StateEstimate(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="state_estimates"
    )

    feature_window = models.ForeignKey(
        "telemetry.FeatureWindow",
        on_delete=models.CASCADE,
        related_name="state_estimates"
    )

    model_version = models.ForeignKey(
        "intelligence.ModelVersion",
        on_delete=models.PROTECT,
        related_name="state_estimates"
    )

    timestamp = models.DateTimeField(db_index=True)

    fatigue_score = models.FloatField()

    workload_score = models.FloatField()

    stress_score = models.FloatField()

    recovery_score = models.FloatField()

    overall_risk_score = models.FloatField()

    fatigue_state = models.CharField(max_length=50)

    overall_state = models.CharField(max_length=50)

    confidence = models.FloatField()

    explanation = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mission_id} - {self.timestamp}"