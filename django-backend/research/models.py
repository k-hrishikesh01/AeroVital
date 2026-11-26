"""Research Models for AeroVital.

Provides isolated research persistence for experimental simulation runs,
intelligence engine evaluations, and scenario analyses.

STRICT ISOLATION GUARANTEES:
1. Research tables never link to or modify operational tables (telemetry_telemetry,
   missions_mission, alerts_alert, pilots_pilot, intelligence_stateestimate).
2. Raw dataset observations remain in versioned filesystem storage; only
   execution parameters, provenance metadata, summary metrics, and window evaluations are persisted.
"""

import uuid
from django.conf import settings
from django.db import models


class ResearchRun(models.Model):
    """Immutable record of an intelligence engine execution run on research data."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run_id = models.CharField(max_length=100, unique=True, db_index=True)

    # Provenance & Versioning
    dataset_id = models.CharField(max_length=100, default="aerovital-synthetic-v1")
    dataset_version = models.CharField(max_length=50, default="1.0.0")
    dataset_checksum = models.CharField(max_length=64, blank=True)
    generator_version = models.CharField(max_length=50, default="1.0.0")
    engine_version = models.CharField(max_length=50, default="1.0.0")
    estimator_id = models.CharField(max_length=100, default="ProvisionalRuleBasedEstimator")
    code_revision = models.CharField(max_length=100, default="715e784")
    random_seed = models.IntegerField(null=True, blank=True)

    # Target Scope
    session_id = models.CharField(max_length=50, db_index=True)
    participant_id = models.CharField(max_length=50, db_index=True)
    scenario = models.CharField(max_length=100, db_index=True)

    # Execution Parameters
    window_duration_sec = models.FloatField(default=60.0)
    step_sec = models.FloatField(default=1.0)
    parameters = models.JSONField(default=dict, blank=True)

    # Performance & Aggregates
    total_samples_processed = models.IntegerField(default=0)
    total_windows_evaluated = models.IntegerField(default=0)
    execution_duration_sec = models.FloatField(default=0.0)
    throughput_samples_per_sec = models.FloatField(default=0.0)

    # Results & Metrics
    mean_confidence = models.FloatField(null=True, blank=True)
    mean_sqi = models.FloatField(null=True, blank=True)
    abstention_rate_pct = models.FloatField(default=0.0)
    state_breakdown = models.JSONField(default=dict, blank=True)
    dominant_factors_summary = models.JSONField(default=list, blank=True)
    
    # Detailed Window Outputs (list of window evaluations)
    window_outputs = models.JSONField(default=list, blank=True)

    # Metadata & User
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="research_runs",
    )
    notes = models.TextField(blank=True)
    disclaimer = models.CharField(
        max_length=255,
        default="Provisional research execution for testing; not clinically or operationally validated.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Research Run"
        verbose_name_plural = "Research Runs"

    def __str__(self):
        return f"{self.run_id} ({self.session_id} - {self.scenario})"
