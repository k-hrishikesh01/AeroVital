from rest_framework import generics

from .models import Telemetry
from .serializers import TelemetrySerializer


class TelemetryListCreateView(generics.ListCreateAPIView):
    queryset = Telemetry.objects.all().order_by("-timestamp")
    serializer_class = TelemetrySerializer