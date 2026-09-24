from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Alert, MissionEvent
from .serializers import AlertSerializer, MissionEventSerializer


class AlertListCreateView(generics.ListCreateAPIView):
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Alert.objects.all().order_by("-timestamp")
        mission_id = self.request.query_params.get("mission")
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        pilot_id = self.request.query_params.get("pilot")
        if pilot_id:
            qs = qs.filter(pilot_id=pilot_id)
        severity = self.request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity.upper())
        unack = self.request.query_params.get("unacknowledged")
        if unack and unack.lower() in ("true", "1"):
            qs = qs.filter(acknowledged=False)
        return qs[:100]


class AlertDetailView(generics.RetrieveAPIView):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]


class AlertAcknowledgeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            alert = Alert.objects.get(pk=pk)
        except Alert.DoesNotExist:
            return Response({"detail": "Alert not found."}, status=status.HTTP_404_NOT_FOUND)

        alert.acknowledged = True
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=["acknowledged", "acknowledged_at"])
        return Response(AlertSerializer(alert).data)


class MissionEventListCreateView(generics.ListCreateAPIView):
    queryset = MissionEvent.objects.all().order_by("-timestamp")
    serializer_class = MissionEventSerializer
    permission_classes = [permissions.IsAuthenticated]