import uuid
from django.db import models


class Pilot(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    pilot_code = models.CharField(
        max_length=100,
        unique=True
    )
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    sex = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pilot_code
