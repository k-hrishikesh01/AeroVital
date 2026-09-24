import uuid
from django.db import models
from backend.core.schemas.telemetry import TelemetrySample


class Telemetry(models.Model):
    id = models.BigAutoField(primary_key=True)

    pilot = models.ForeignKey(
        "pilots.Pilot",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="telemetry",
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="telemetry",
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="telemetry",
    )

    timestamp = models.DateTimeField(db_index=True)

    # Physiological channels (nullable, never fabricated)
    heart_rate = models.FloatField(null=True, blank=True)
    # rr_interval can be scalar float or list of floats per Core contract
    rr_interval = models.JSONField(null=True, blank=True)
    spo2 = models.FloatField(null=True, blank=True)
    skin_temperature = models.FloatField(null=True, blank=True)
    # activity_level can be str or float per Core contract
    activity_level = models.JSONField(null=True, blank=True)
    steps = models.IntegerField(null=True, blank=True)

    # 3-axis accelerometer readings
    accel_x = models.FloatField(null=True, blank=True)
    accel_y = models.FloatField(null=True, blank=True)
    accel_z = models.FloatField(null=True, blank=True)

    battery_level = models.FloatField(null=True, blank=True)

    # Original wearable payload untouched for provenance
    raw_payload = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Telemetry"

    def __str__(self):
        return f"Telemetry {self.device_id or 'unknown'} @ {self.timestamp}"

    def to_core_sample(self) -> TelemetrySample:
        """Convert this model instance into a verified Core TelemetrySample."""
        return TelemetrySample(
            timestamp=self.timestamp,
            heart_rate=self.heart_rate,
            rr_interval=self.rr_interval,
            spo2=self.spo2,
            skin_temperature=self.skin_temperature,
            activity_level=self.activity_level,
            steps=self.steps,
            accel_x=self.accel_x,
            accel_y=self.accel_y,
            accel_z=self.accel_z,
            battery_level=self.battery_level,
            raw_payload=self.raw_payload or None,
        )


class SignalQuality(models.Model):
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
        related_name="signal_qualities",
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signal_qualities",
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="signal_qualities",
    )

    timestamp = models.DateTimeField(db_index=True)
    overall_sqi = models.FloatField()
    is_telemetry_acceptable = models.BooleanField(default=True)
    motion_corruption_index = models.FloatField(default=0.0)
    channels = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "Signal Qualities"

    def __str__(self):
        return f"SQI {self.overall_sqi:.2f} @ {self.timestamp}"


class FeatureWindow(models.Model):
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
        related_name="feature_windows",
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feature_windows",
    )
    mission = models.ForeignKey(
        "missions.Mission",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feature_windows",
    )

    window_start = models.DateTimeField(db_index=True)
    window_end = models.DateTimeField(db_index=True)
    window_duration_sec = models.FloatField()

    # Core extracted feature metrics
    mean_hr = models.FloatField(null=True, blank=True)
    min_hr = models.FloatField(null=True, blank=True)
    max_hr = models.FloatField(null=True, blank=True)
    hr_std = models.FloatField(null=True, blank=True)

    mean_rr_ms = models.FloatField(null=True, blank=True)
    sdnn_ms = models.FloatField(null=True, blank=True)
    rmssd_ms = models.FloatField(null=True, blank=True)
    pnn50_percent = models.FloatField(null=True, blank=True)

    mean_magnitude = models.FloatField(null=True, blank=True)
    activity_intensity = models.FloatField(null=True, blank=True)

    baseline_available = models.BooleanField(default=False)
    hr_deviation_from_baseline = models.FloatField(null=True, blank=True)
    hrv_rmssd_ratio_to_baseline = models.FloatField(null=True, blank=True)

    # Full features payload for completeness
    features_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-window_end"]

    def __str__(self):
        return f"Window [{self.window_start} -> {self.window_end}]"