from rest_framework import serializers

from .models import Telemetry, SignalQuality, FeatureWindow
from intelligence.models import StateEstimate


class TelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Telemetry
        fields = [
            "id",
            "pilot",
            "device",
            "mission",
            "timestamp",
            "heart_rate",
            "rr_interval",
            "spo2",
            "skin_temperature",
            "activity_level",
            "steps",
            "accel_x",
            "accel_y",
            "accel_z",
            "battery_level",
            "raw_payload",
            "received_at",
        ]
        read_only_fields = ["id", "received_at"]


class SignalQualitySerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalQuality
        fields = [
            "id",
            "pilot",
            "device",
            "mission",
            "timestamp",
            "overall_sqi",
            "is_telemetry_acceptable",
            "motion_corruption_index",
            "channels",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class FeatureWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureWindow
        fields = [
            "id",
            "pilot",
            "device",
            "mission",
            "window_start",
            "window_end",
            "window_duration_sec",
            "mean_hr",
            "min_hr",
            "max_hr",
            "hr_std",
            "mean_rr_ms",
            "sdnn_ms",
            "rmssd_ms",
            "pnn50_percent",
            "mean_magnitude",
            "activity_intensity",
            "baseline_available",
            "hr_deviation_from_baseline",
            "hrv_rmssd_ratio_to_baseline",
            "features_payload",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]