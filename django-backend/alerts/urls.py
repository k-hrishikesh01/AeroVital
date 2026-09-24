from django.urls import path
from .views import (
    AlertListCreateView,
    AlertDetailView,
    AlertAcknowledgeView,
    MissionEventListCreateView,
)

urlpatterns = [
    path("", AlertListCreateView.as_view(), name="alert-list-create"),
    path("<uuid:pk>/", AlertDetailView.as_view(), name="alert-detail"),
    path("<uuid:pk>/acknowledge/", AlertAcknowledgeView.as_view(), name="alert-acknowledge"),
    path("mission-events/", MissionEventListCreateView.as_view(), name="mission-event-list-create"),
]
