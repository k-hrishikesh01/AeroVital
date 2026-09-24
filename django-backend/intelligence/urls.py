from django.urls import path
from .views import (
    StateEstimateListView,
    CurrentStateView,
    BaselineListCreateView,
    BaselineDetailView,
    ModelVersionListView,
)

urlpatterns = [
    path("state-estimates/", StateEstimateListView.as_view(), name="state-estimate-list"),
    path("estimates/", StateEstimateListView.as_view(), name="estimate-list"),
    path("current-state/", CurrentStateView.as_view(), name="current-state"),
    path("baselines/", BaselineListCreateView.as_view(), name="baseline-list-create"),
    path("baselines/<uuid:pk>/", BaselineDetailView.as_view(), name="baseline-detail"),
    path("model-versions/", ModelVersionListView.as_view(), name="model-version-list"),
]