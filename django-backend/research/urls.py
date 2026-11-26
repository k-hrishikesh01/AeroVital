"""URL configuration for AeroVital Research App."""

from django.urls import path
from research.views import (
    ResearchExecuteView,
    ResearchExportView,
    ResearchManifestView,
    ResearchParticipantsView,
    ResearchRunCompareView,
    ResearchRunDetailView,
    ResearchRunListView,
    ResearchSessionsView,
    ResearchSessionTimeseriesView,
)

urlpatterns = [
    path("manifest/", ResearchManifestView.as_view(), name="research-manifest"),
    path("participants/", ResearchParticipantsView.as_view(), name="research-participants"),
    path("sessions/", ResearchSessionsView.as_view(), name="research-sessions"),
    path("sessions/<str:session_id>/timeseries/", ResearchSessionTimeseriesView.as_view(), name="research-timeseries"),
    path("execute/", ResearchExecuteView.as_view(), name="research-execute"),
    path("runs/", ResearchRunListView.as_view(), name="research-runs"),
    path("runs/compare/", ResearchRunCompareView.as_view(), name="research-runs-compare"),
    path("runs/<str:run_id>/", ResearchRunDetailView.as_view(), name="research-run-detail"),
    path("export/<str:session_id>/", ResearchExportView.as_view(), name="research-export"),
]
