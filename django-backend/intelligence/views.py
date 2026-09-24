from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import StateEstimate, Baseline, ModelVersion
from .serializers import (
    StateEstimateSerializer,
    BaselineSerializer,
    ModelVersionSerializer,
)
from missions.models import Mission
from telemetry.models import Telemetry, SignalQuality
from pilots.permissions import enforce_pilot_scoping, IsStaffOrPilotOwner, get_user_pilot


class StateEstimateListView(generics.ListAPIView):
    serializer_class = StateEstimateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = StateEstimate.objects.all().order_by("-timestamp")
        qs = enforce_pilot_scoping(self.request, qs, pilot_field="pilot")
        mission_id = self.request.query_params.get("mission")
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        fatigue_state = self.request.query_params.get("fatigue_state")
        if fatigue_state:
            qs = qs.filter(fatigue_state=fatigue_state.upper())
        limit = min(int(self.request.query_params.get("limit", 100)), 500)
        return qs[:limit]


class CurrentStateView(APIView):
    """Provides current fatigue state, confidence, signal quality, and freshness for dashboard."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        mission_id = request.query_params.get("mission")
        pilot_id = request.query_params.get("pilot")

        user_pilot = get_user_pilot(request.user)
        if user_pilot is not None and not (request.user.is_staff or request.user.is_superuser):
            if pilot_id and str(pilot_id) != str(user_pilot.id):
                raise PermissionDenied("You do not have permission to view another pilot's current state.")
            pilot_id = str(user_pilot.id)

        qs = StateEstimate.objects.all().order_by("-timestamp")
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        if pilot_id:
            qs = qs.filter(pilot_id=pilot_id)

        latest_estimate = qs.first()

        # Telemetry freshness
        telemetry_qs = Telemetry.objects.all().order_by("-timestamp")
        if mission_id:
            telemetry_qs = telemetry_qs.filter(mission_id=mission_id)
        if pilot_id:
            telemetry_qs = telemetry_qs.filter(pilot_id=pilot_id)
        latest_telemetry = telemetry_qs.first()

        # Latest Signal Quality
        sqi_qs = SignalQuality.objects.all().order_by("-timestamp")
        if mission_id:
            sqi_qs = sqi_qs.filter(mission_id=mission_id)
        if pilot_id:
            sqi_qs = sqi_qs.filter(pilot_id=pilot_id)
        latest_sqi = sqi_qs.first()

        # Mission info
        mission_info = None
        if mission_id:
            m = Mission.objects.filter(id=mission_id).first()
            if m:
                mission_info = {
                    "id": str(m.id),
                    "code": m.mission_code,
                    "status": m.status,
                    "phase": m.current_phase,
                    "g_load": m.external_g_load,
                }

        freshness_sec = None
        if latest_telemetry:
            now = timezone.now()
            delta = now - latest_telemetry.timestamp
            freshness_sec = max(0.0, delta.total_seconds())

        response_data = {
            "current_state": latest_estimate.fatigue_state if latest_estimate else "INSUFFICIENT_DATA",
            "fatigue_score": latest_estimate.fatigue_score if latest_estimate else None,
            "confidence": latest_estimate.confidence if latest_estimate else 0.0,
            "overall_sqi": latest_estimate.overall_sqi if latest_estimate else (latest_sqi.overall_sqi if latest_sqi else 0.0),
            "dominant_factors": latest_estimate.dominant_factors if latest_estimate else ["No estimation yet available"],
            "evidence": latest_estimate.evidence if latest_estimate else {},
            "baseline_version": latest_estimate.baseline_version_used if latest_estimate else None,
            "timestamp": latest_estimate.timestamp if latest_estimate else None,
            "last_telemetry_timestamp": latest_telemetry.timestamp if latest_telemetry else None,
            "freshness_sec": freshness_sec,
            "mission": mission_info,
        }

        return Response(response_data)


class BaselineListCreateView(generics.ListCreateAPIView):
    serializer_class = BaselineSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Baseline.objects.all().order_by("-created_at")
        qs = enforce_pilot_scoping(self.request, qs, pilot_field="pilot")
        return qs

    def perform_create(self, serializer):
        user_pilot = get_user_pilot(self.request.user)
        if user_pilot is not None and not (self.request.user.is_staff or self.request.user.is_superuser):
            serializer.save(pilot=user_pilot)
        else:
            serializer.save()


class BaselineDetailView(generics.RetrieveUpdateAPIView):
    queryset = Baseline.objects.all()
    serializer_class = BaselineSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrPilotOwner]


class ModelVersionListView(generics.ListAPIView):
    queryset = ModelVersion.objects.filter(is_active=True).order_by("-created_at")
    serializer_class = ModelVersionSerializer
    permission_classes = [permissions.IsAuthenticated]
