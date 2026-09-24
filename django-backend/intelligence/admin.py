from django.contrib import admin
from .models import Baseline, ModelVersion, StateEstimate


@admin.register(Baseline)
class BaselineAdmin(admin.ModelAdmin):
    list_display = ("id", "pilot", "baseline_version", "resting_heart_rate", "baseline_rmssd", "is_calibrated", "is_active", "created_at")
    list_filter = ("is_calibrated", "is_active")
    search_fields = ("pilot__pilot_code", "baseline_version")


@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ("estimator_id", "name", "version", "is_provisional", "confidence_threshold", "is_active")
    list_filter = ("is_provisional", "is_active")


@admin.register(StateEstimate)
class StateEstimateAdmin(admin.ModelAdmin):
    list_display = ("id", "pilot", "mission", "timestamp", "fatigue_state", "fatigue_score", "confidence", "overall_sqi")
    list_filter = ("fatigue_state", "mission")
    search_fields = ("pilot__pilot_code", "mission__mission_code")
