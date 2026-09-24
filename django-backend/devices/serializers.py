from rest_framework import serializers
from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            "id",
            "pilot",
            "device_uid",
            "device_type",
            "manufacturer",
            "model",
            "firmware_version",
            "connection_type",
            "sampling_rate",
            "is_active",
            "last_seen_at",
            "created_at",
        ]
        read_only_fields = ["id", "last_seen_at", "created_at"]
