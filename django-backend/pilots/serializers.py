from rest_framework import serializers
from .models import Pilot


class PilotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pilot
        fields = [
            "id",
            "pilot_code",
            "name",
            "age",
            "sex",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
