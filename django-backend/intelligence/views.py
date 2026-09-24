from rest_framework import generics

from .models import StateEstimate
from .serializers import StateEstimateSerializer


class StateEstimateListView(generics.ListAPIView):
    queryset = StateEstimate.objects.all().order_by("-timestamp")
    serializer_class = StateEstimateSerializer
