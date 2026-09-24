from django.urls import path
from .views import (
    MissionListCreateView,
    MissionDetailView,
    MissionCompleteView,
    MissionEventListCreateView,
)

urlpatterns = [
    path("", MissionListCreateView.as_view(), name="mission-list-create"),
    path("<uuid:pk>/", MissionDetailView.as_view(), name="mission-detail"),
    path("<uuid:pk>/complete/", MissionCompleteView.as_view(), name="mission-complete"),
    path("<uuid:mission_id>/events/", MissionEventListCreateView.as_view(), name="mission-events"),
]
