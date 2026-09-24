import uuid
from django.db import models


class Telemetry(models.Model):
    id = models.BigAutoField(primary_key=True)

    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="telemetry"
    )

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="telemetry"
    )

    timestamp = models.DateTimeField(db_index=True)

    heart_rate = models.FloatField(null=True, blank=True)
    rr_interval = models.FloatField(null=True, blank=True)
    spo2 = models.FloatField(null=True, blank=True)
    skin_temperature = models.FloatField(null=True, blank=True)
    activity_level = models.FloatField(null=True, blank=True)
    steps = models.IntegerField(null=True, blank=True)

    accel_x = models.FloatField(null=True, blank=True)
    accel_y = models.FloatField(null=True, blank=True)
    accel_z = models.FloatField(null=True, blank=True)

    battery_level = models.FloatField(null=True, blank=True)

    # Original wearable payload.
    # This must remain untouched.
    raw_payload = models.JSONField(default=dict)

    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_id} - {self.timestamp}"


class SignalQuality(models.Model):

    class QualityStatus(models.TextChoices):
        GOOD = "GOOD", "Good"
        ACCEPTABLE = "ACCEPTABLE", "Acceptable"
        POOR = "POOR", "Poor"
        INVALID = "INVALID", "Invalid"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="signal_quality"
    )

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="signal_quality"
    )

    timestamp = models.DateTimeField(db_index=True)

    signal_type = models.CharField(max_length=100)

    quality_score = models.FloatField()

    quality_status = models.CharField(
        max_length=20,
        choices=QualityStatus.choices
    )

    artifact_ratio = models.FloatField(
        null=True,
        blank=True
    )

    missing_ratio = models.FloatField(
        null=True,
        blank=True
    )

    noise_detected = models.BooleanField(default=False)

    quality_flags = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.signal_type} - {self.quality_status}"


class FeatureWindow(models.Model):

    class FeatureStatus(models.TextChoices):
        VALID = "VALID", "Valid"
        PARTIAL = "PARTIAL", "Partial"
        INVALID = "INVALID", "Invalid"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        related_name="feature_windows"
    )

    start_time = models.DateTimeField(db_index=True)

    end_time = models.DateTimeField(db_index=True)

    window_duration = models.IntegerField()

    sample_count = models.IntegerField()

    signal_quality = models.FloatField()

    feature_status = models.CharField(
        max_length=20,
        choices=FeatureStatus.choices
    )

    mean_hr = models.FloatField(null=True, blank=True)
    hr_std = models.FloatField(null=True, blank=True)
    mean_rr = models.FloatField(null=True, blank=True)
    rmssd = models.FloatField(null=True, blank=True)
    sdnn = models.FloatField(null=True, blank=True)

    activity_mean = models.FloatField(null=True, blank=True)
    spo2_mean = models.FloatField(null=True, blank=True)
    skin_temp_mean = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.mission_id} - {self.start_time}"