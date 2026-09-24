from django.urls import path
from .views import PilotListCreateView, PilotDetailView

urlpatterns = [
    path("", PilotListCreateView.as_view(), name="pilot-list-create"),
    path("<uuid:pk>/", PilotDetailView.as_view(), name="pilot-detail"),
]
