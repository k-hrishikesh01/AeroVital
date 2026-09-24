from django.contrib import admin
from .models import Telemetry, SignalQuality, FeatureWindow


@admin.register(Telemetry)
class TelemetryAdmin(admin.ModelAdmin):
    list_display = ("id", "pilot", "device", "mission", "timestamp", "heart_rate", "spo2", "battery_level")
    search_fields = ("device__device_uid", "pilot__pilot_code")
    list_filter = ("mission", "device")


@admin.register(SignalQuality)
class SignalQualityAdmin(admin.ModelAdmin):
    list_display = ("id", "pilot", "mission", "timestamp", "overall_sqi", "is_telemetry_acceptable")
    list_filter = ("is_telemetry_acceptable", "mission")


@admin.register(FeatureWindow)
class FeatureWindowAdmin(admin.ModelAdmin):
    list_display = ("id", "pilot", "mission", "window_start", "window_end", "mean_hr", "rmssd_ms", "baseline_available")
    list_filter = ("baseline_available", "mission")
