import uuid
from django.db import models


class Device(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    pilot = models.ForeignKey(
        "pilots.Pilot",
        on_delete=models.CASCADE,
        related_name="devices"
    )
    device_uid = models.CharField(max_length=255)
    device_type = models.CharField(max_length=100)
    manufacturer = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    firmware_version = models.CharField(max_length=100)
    connection_type = models.CharField(max_length=100)
    sampling_rate = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.device_uid