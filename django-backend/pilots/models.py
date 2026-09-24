import uuid
from django.conf import settings
from django.db import models


class Pilot(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pilot_profile",
    )
    pilot_code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True, blank=True)
    sex = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pilot_code} ({self.name})"
