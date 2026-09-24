from django.contrib import admin
from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_uid", "pilot", "device_type", "model", "is_active", "last_seen_at")
    search_fields = ("device_uid", "manufacturer", "model")
    list_filter = ("device_type", "is_active", "connection_type")
