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
        editable=False
    )

    pilot = models.ForeignKey(
        "pilots.Pilot",
        on_delete=models.CASCADE,
        related_name="missions"
    )

    mission_code = models.CharField(
        max_length=100,
        unique=True
    )

    mission_type = models.CharField(max_length=100)

    start_time = models.DateTimeField()

    end_time = models.DateTimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED
    )

    environment = models.JSONField(default=dict)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.mission_code