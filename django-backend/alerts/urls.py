from django.urls import path

from .views import (
    AlertListCreateView,
    MissionEventListCreateView,
)

urlpatterns = [
    path("alerts/", AlertListCreateView.as_view(), name="alert-list-create"),
    path("mission-events/", MissionEventListCreateView.as_view(), name="mission-event-list-create"),
]
