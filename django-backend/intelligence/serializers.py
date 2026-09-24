from rest_framework import serializers

from .models import StateEstimate


class StateEstimateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StateEstimate
        fields = "__all__"