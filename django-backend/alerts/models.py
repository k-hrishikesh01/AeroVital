import uuid
from django.db import models


class Alert(models.Model):

    class Severity(models.TextChoices):
        INFO = "INFO", "Info"
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

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
        related_name="alerts",
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alerts",
    )
    state_estimate = models.ForeignKey(
        "intelligence.StateEstimate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alerts",
    )
    timestamp = models.DateTimeField(db_index=True)
    alert_type = models.CharField(max_length=100)
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFO,
    )
    message = models.TextField()
    trigger_state = models.CharField(max_length=50, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.severity}] {self.alert_type} @ {self.timestamp}"


class MissionEvent(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="events",
    )
    timestamp = models.DateTimeField(db_index=True)
    event_type = models.CharField(max_length=100)
    event_value = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.event_type} @ {self.timestamp} ({self.mission.mission_code})"