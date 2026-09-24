from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Telemetry, SignalQuality, FeatureWindow
from .serializers import (
    TelemetrySerializer,
    SignalQualitySerializer,
    FeatureWindowSerializer,
)
from .services import ingest_telemetry_sample, evaluate_batch_window_samples
from intelligence.serializers import StateEstimateSerializer


class TelemetryIngestAndListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Telemetry.objects.all().order_by("-timestamp")
        mission_id = request.query_params.get("mission")
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        device_id = request.query_params.get("device")
        if device_id:
            qs = qs.filter(device_id=device_id)
        pilot_id = request.query_params.get("pilot")
        if pilot_id:
            qs = qs.filter(pilot_id=pilot_id)

        limit = min(int(request.query_params.get("limit", 100)), 500)
        serializer = TelemetrySerializer(qs[:limit], many=True)
        return Response(serializer.data)

    def post(self, request):
        # Resolve pilot or device from authenticated user if available
        pilot = None
        if hasattr(request.user, "pilot_profile"):
            pilot = request.user.pilot_profile

        result = ingest_telemetry_sample(
            data=request.data,
            pilot=pilot,
        )

        response_data = {
            "telemetry": TelemetrySerializer(result["telemetry"]).data,
            "status": result["status"],
            "estimate": StateEstimateSerializer(result["estimate"]).data if result["estimate"] else None,
            "quality": SignalQualitySerializer(result["quality"]).data if result["quality"] else None,
            "alert": {
                "id": str(result["alert"].id),
                "alert_type": result["alert"].alert_type,
                "severity": result["alert"].severity,
                "message": result["alert"].message,
            } if result["alert"] else None,
        }

        return Response(response_data, status=status.HTTP_201_CREATED)


class TelemetryBatchIngestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        samples_data = request.data.get("samples")
        if not samples_data or not isinstance(samples_data, list):
            return Response(
                {"detail": "A list of 'samples' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pilot = None
        if hasattr(request.user, "pilot_profile"):
            pilot = request.user.pilot_profile

        result = evaluate_batch_window_samples(
            samples_data=samples_data,
            pilot=pilot,
        )

        response_data = {
            "status": result["status"],
            "telemetry_count": result["telemetry_count"],
            "estimate": StateEstimateSerializer(result["estimate"]).data if result.get("estimate") else None,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class SignalQualityListView(generics.ListAPIView):
    serializer_class = SignalQualitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SignalQuality.objects.all().order_by("-timestamp")
        mission_id = self.request.query_params.get("mission")
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        return qs[:100]


class FeatureWindowListView(generics.ListAPIView):
    serializer_class = FeatureWindowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = FeatureWindow.objects.all().order_by("-window_end")
        mission_id = self.request.query_params.get("mission")
        if mission_id:
            qs = qs.filter(mission_id=mission_id)
        return qs[:100]