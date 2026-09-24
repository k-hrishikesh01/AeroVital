from rest_framework import generics, permissions
from .models import Pilot
from .serializers import PilotSerializer


class PilotListCreateView(generics.ListCreateAPIView):
    queryset = Pilot.objects.all().order_by("pilot_code")
    serializer_class = PilotSerializer
    permission_classes = [permissions.IsAuthenticated]


class PilotDetailView(generics.RetrieveUpdateAPIView):
    queryset = Pilot.objects.all()
    serializer_class = PilotSerializer
    permission_classes = [permissions.IsAuthenticated]
