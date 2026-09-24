from rest_framework import serializers

from .models import Alert, MissionEvent


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = "__all__"


class MissionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissionEvent
        fields = "__all__"