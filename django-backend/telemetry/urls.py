from django.urls import path

from .views import TelemetryListCreateView


urlpatterns = [
    path("", TelemetryListCreateView.as_view(), name="telemetry-list-create"),
]