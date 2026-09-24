from rest_framework import serializers
from .models import Mission
from alerts.models import MissionEvent


class MissionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissionEvent
        fields = ["id", "mission", "timestamp", "event_type", "event_value", "description", "created_at"]
        read_only_fields = ["id", "mission", "created_at"]


class MissionSerializer(serializers.ModelSerializer):
    events = MissionEventSerializer(many=True, read_only=True)

    class Meta:
        model = Mission
        fields = [
            "id",
            "pilot",
            "mission_code",
            "mission_type",
            "current_phase",
            "external_g_load",
            "start_time",
            "end_time",
            "status",
            "environment",
            "created_at",
            "events",
        ]
        read_only_fields = ["id", "created_at"]
