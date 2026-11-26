"""Serializers for AeroVital Research App."""

from rest_framework import serializers
from research.models import ResearchRun


class ResearchRunListSerializer(serializers.ModelSerializer):
    """Compact serializer for listing historical research runs."""

    class Meta:
        model = ResearchRun
        fields = [
            "id",
            "run_id",
            "dataset_id",
            "dataset_version",
            "engine_version",
            "session_id",
            "participant_id",
            "scenario",
            "total_samples_processed",
            "total_windows_evaluated",
            "execution_duration_sec",
            "throughput_samples_per_sec",
            "mean_confidence",
            "mean_sqi",
            "abstention_rate_pct",
            "state_breakdown",
            "created_at",
            "notes",
            "disclaimer",
        ]


class ResearchRunDetailSerializer(serializers.ModelSerializer):
    """Complete serializer including per-window outputs and trace summaries."""

    class Meta:
        model = ResearchRun
        fields = [
            "id",
            "run_id",
            "dataset_id",
            "dataset_version",
            "dataset_checksum",
            "generator_version",
            "engine_version",
            "estimator_id",
            "code_revision",
            "random_seed",
            "session_id",
            "participant_id",
            "scenario",
            "window_duration_sec",
            "step_sec",
            "parameters",
            "total_samples_processed",
            "total_windows_evaluated",
            "execution_duration_sec",
            "throughput_samples_per_sec",
            "mean_confidence",
            "mean_sqi",
            "abstention_rate_pct",
            "state_breakdown",
            "dominant_factors_summary",
            "window_outputs",
            "created_at",
            "notes",
            "disclaimer",
        ]


class ExecuteRunRequestSerializer(serializers.Serializer):
    """Request payload serializer for POST /api/v1/research/execute/."""

    session_id = serializers.RegexField(
        regex=r"^SYN-S\d{3}$",
        required=True,
        error_messages={"invalid": "Invalid session identifier format (expected format: 'SYN-S001')."},
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
