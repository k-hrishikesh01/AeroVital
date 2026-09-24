from django.contrib import admin
from .models import Alert, MissionEvent


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "pilot", "mission", "alert_type", "severity", "timestamp", "acknowledged")
    list_filter = ("severity", "alert_type", "acknowledged")
    search_fields = ("alert_type", "message")


@admin.register(MissionEvent)
class MissionEventAdmin(admin.ModelAdmin):
    list_display = ("id", "mission", "event_type", "timestamp")
    list_filter = ("event_type", "mission")
    search_fields = ("event_type", "description")
