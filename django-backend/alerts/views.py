from rest_framework import generics

from .models import Alert, MissionEvent
from .serializers import AlertSerializer, MissionEventSerializer


class AlertListCreateView(generics.ListCreateAPIView):
    queryset = Alert.objects.all().order_by("-timestamp")
    serializer_class = AlertSerializer


class MissionEventListCreateView(generics.ListCreateAPIView):
    queryset = MissionEvent.objects.all().order_by("-timestamp")
    serializer_class = MissionEventSerializer