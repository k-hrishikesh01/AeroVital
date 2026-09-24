from django.urls import path

from .views import StateEstimateListView


urlpatterns = [
    path("state-estimates/", StateEstimateListView.as_view(), name="state-estimate-list"),
]