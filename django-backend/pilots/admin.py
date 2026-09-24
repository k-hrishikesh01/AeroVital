from django.contrib import admin
from .models import Pilot


@admin.register(Pilot)
class PilotAdmin(admin.ModelAdmin):
    list_display = ("pilot_code", "name", "age", "sex", "is_active", "created_at")
    search_fields = ("pilot_code", "name")
    list_filter = ("is_active", "sex")
