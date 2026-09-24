import uuid
from django.db import models


class Mission(models.Model):

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    pilot = models.ForeignKey(
        "pilots.Pilot",
        on_delete=models.CASCADE,
        related_name="missions",
    )
    mission_code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )
    mission_type = models.CharField(max_length=100, default="ROUTINE_SORTIE")
    current_phase = models.CharField(max_length=50, default="CRUISE", blank=True)
    external_g_load = models.FloatField(null=True, blank=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    environment = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mission_code} ({self.status})"