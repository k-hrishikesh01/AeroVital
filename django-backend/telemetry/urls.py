from django.urls import path
from .views import (
    TelemetryIngestAndListView,
    TelemetryBatchIngestView,
    SignalQualityListView,
    FeatureWindowListView,
)

urlpatterns = [
    path("", TelemetryIngestAndListView.as_view(), name="telemetry-ingest-list"),
    path("batch/", TelemetryBatchIngestView.as_view(), name="telemetry-batch-ingest"),
    path("signal-quality/", SignalQualityListView.as_view(), name="signal-quality-list"),
    path("features/", FeatureWindowListView.as_view(), name="feature-window-list"),
]