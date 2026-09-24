from django.contrib import admin
from .models import Mission


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("mission_code", "pilot", "mission_type", "current_phase", "status", "start_time", "end_time")
    search_fields = ("mission_code", "mission_type")
    list_filter = ("status", "current_phase")
