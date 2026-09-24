from rest_framework import serializers

from .models import Telemetry


class TelemetrySerializer(serializers.ModelSerializer):

    def validate_heart_rate(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Heart rate cannot be negative."
            )
        return value

    class Meta:
        model = Telemetry
        fields = "__all__"