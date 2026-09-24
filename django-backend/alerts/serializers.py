from rest_framework import serializers
from missions.models import Mission
from .models import Alert, MissionEvent


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            "id",
            "pilot",
            "mission",
            "state_estimate",
            "timestamp",
            "alert_type",
            "severity",
            "message",
            "trigger_state",
            "confidence",
            "acknowledged",
            "acknowledged_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class MissionEventSerializer(serializers.ModelSerializer):
    mission = serializers.PrimaryKeyRelatedField(queryset=Mission.objects.all(), required=False)

    class Meta:
        model = MissionEvent
        fields = [
            "id",
            "mission",
            "timestamp",
            "event_type",
            "event_value",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]