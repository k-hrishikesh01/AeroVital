from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Mission
from .serializers import MissionSerializer, MissionEventSerializer
from alerts.models import MissionEvent
from pilots.permissions import enforce_pilot_scoping, IsStaffOrPilotOwner, get_user_pilot
from telemetry.services import pipeline_manager


class MissionListCreateView(generics.ListCreateAPIView):
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Mission.objects.all().order_by("-start_time")
        qs = enforce_pilot_scoping(self.request, qs, pilot_field="pilot")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs


class MissionDetailView(generics.RetrieveUpdateAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrPilotOwner]


class MissionCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            mission = Mission.objects.get(pk=pk)
        except Mission.DoesNotExist:
            return Response({"detail": "Mission not found."}, status=status.HTTP_404_NOT_FOUND)

        user_pilot = get_user_pilot(request.user)
        if user_pilot is not None and not (request.user.is_staff or request.user.is_superuser):
            if mission.pilot and mission.pilot.id != user_pilot.id:
                raise PermissionDenied("You do not have permission to complete another pilot's mission.")

        mission.status = Mission.Status.COMPLETED
        mission.end_time = timezone.now()
        mission.save(update_fields=["status", "end_time"])

        # Reset stateful pipeline buffer session for completed mission
        pipeline_manager.reset_session(mission=mission, pilot=mission.pilot)

        return Response(MissionSerializer(mission).data)


class MissionEventListCreateView(generics.ListCreateAPIView):
    serializer_class = MissionEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MissionEvent.objects.filter(mission_id=self.kwargs["mission_id"]).order_by("-timestamp")

    def perform_create(self, serializer):
        serializer.save(mission_id=self.kwargs["mission_id"])
