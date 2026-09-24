from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Mission
from .serializers import MissionSerializer, MissionEventSerializer
from alerts.models import MissionEvent


class MissionListCreateView(generics.ListCreateAPIView):
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Mission.objects.all().order_by("-start_time")
        pilot_id = self.request.query_params.get("pilot")
        if pilot_id:
            qs = qs.filter(pilot_id=pilot_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs


class MissionDetailView(generics.RetrieveUpdateAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]


class MissionCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            mission = Mission.objects.get(pk=pk)
        except Mission.DoesNotExist:
            return Response({"detail": "Mission not found."}, status=status.HTTP_404_NOT_FOUND)

        mission.status = Mission.Status.COMPLETED
        mission.end_time = timezone.now()
        mission.save(update_fields=["status", "end_time"])
        return Response(MissionSerializer(mission).data)


class MissionEventListCreateView(generics.ListCreateAPIView):
    serializer_class = MissionEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MissionEvent.objects.filter(mission_id=self.kwargs["mission_id"]).order_by("-timestamp")

    def perform_create(self, serializer):
        serializer.save(mission_id=self.kwargs["mission_id"])
