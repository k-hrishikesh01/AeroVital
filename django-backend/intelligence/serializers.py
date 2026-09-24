from rest_framework import serializers

from .models import StateEstimate, Baseline, ModelVersion


class StateEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StateEstimate
        fields = [
            "id",
            "pilot",
            "mission",
            "feature_window",
            "timestamp",
            "fatigue_state",
            "fatigue_score",
            "confidence",
            "overall_sqi",
            "dominant_factors",
            "estimator_id",
            "is_provisional",
            "disclaimer",
            "confidence_threshold_used",
            "baseline_version_used",
            "evidence",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BaselineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Baseline
        fields = [
            "id",
            "pilot",
            "baseline_version",
            "resting_heart_rate",
            "baseline_rmssd",
            "baseline_sdnn",
            "baseline_mean_rr",
            "calibration_duration_sec",
            "is_calibrated",
            "metadata",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelVersion
        fields = [
            "id",
            "estimator_id",
            "name",
            "version",
            "is_provisional",
            "disclaimer",
            "confidence_threshold",
            "parameters",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]