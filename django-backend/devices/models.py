import uuid
from django.db import models


class Device(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    pilot = models.ForeignKey(
        "pilots.Pilot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
    )
    device_uid = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    device_type = models.CharField(max_length=100, default="WEARABLE")
    manufacturer = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    firmware_version = models.CharField(max_length=100, blank=True)
    connection_type = models.CharField(max_length=100, default="BLE", blank=True)
    sampling_rate = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_uid} ({self.model or self.device_type})"