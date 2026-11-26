"""Research Views for AeroVital.

Provides authenticated API endpoints for synthetic dataset exploration,
telemetry signal visualization, on-demand pipeline execution, and run history comparison.
"""

import csv
import io
import json
from datetime import datetime, timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse

from research.models import ResearchRun
from research.serializers import (
    ExecuteRunRequestSerializer,
    ResearchRunDetailSerializer,
    ResearchRunListSerializer,
)
from research.services import EngineExecutionService, registry


class PassthroughCSVRenderer(BaseRenderer):
    """Custom renderer for direct CSV streaming."""
    media_type = "text/csv"
    format = "csv"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class ResearchManifestView(APIView):
    """GET /api/v1/research/manifest/

    Returns dataset manifest, checksums, schema version, and operational isolation statement.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        manifest = registry.get_manifest()
        return Response(manifest, status=status.HTTP_200_OK)


class ResearchParticipantsView(APIView):
    """GET /api/v1/research/participants/

    Returns 30 synthetic participant profiles and calibrated baseline metrics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        participants = registry.get_participants()
        return Response(participants, status=status.HTTP_200_OK)


class ResearchSessionsView(APIView):
    """GET /api/v1/research/sessions/?scenario=<name>

    Returns 60 session metadata records with optional scenario filtering.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scenario = request.query_params.get("scenario")
        sessions = registry.get_sessions(scenario=scenario)
        return Response(sessions, status=status.HTTP_200_OK)


class ResearchSessionTimeseriesView(APIView):
    """GET /api/v1/research/sessions/<session_id>/timeseries/?downsample=<factor>

    Returns downsampled observation sequence for charting (default downsample=5 for fast UI render).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        downsample_param = request.query_params.get("downsample", "5")
        try:
            downsample = int(downsample_param)
        except ValueError:
            downsample = 5

        records = registry.stream_session_records(
            session_id=session_id,
            downsample_factor=downsample,
        )

        # Build compact presentation-optimized series
        formatted_series = []
        for r in records:
            formatted_series.append({
                "time_sec": r.get("flight_duration_sec"),
                "timestamp": r.get("timestamp"),
                "heart_rate": r.get("heart_rate"),
                "rr_interval": r.get("rr_interval"),
                "spo2": r.get("spo2"),  # null
                "skin_temperature": r.get("skin_temperature"),  # null
                "external_g_load": r.get("external_g_load"),
                "mission_phase": r.get("mission_phase"),
                "activity_level": r.get("activity_level"),
                "accel_z": r.get("accel_z"),
            })

        return Response({
            "session_id": session_id,
            "total_points": len(formatted_series),
            "downsample_factor": downsample,
            "data": formatted_series,
        }, status=status.HTTP_200_OK)


class ResearchExecuteView(APIView):
    """POST /api/v1/research/execute/

    Executes the unmodified AeroVital Core Intelligence Engine on a synthetic session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ExecuteRunRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["session_id"]
        notes = serializer.validated_data.get("notes", "")

        result = EngineExecutionService.execute_session(
            session_id=session_id,
            user=request.user,
            notes=notes,
        )

        return Response(result, status=status.HTTP_201_CREATED)


class ResearchRunListView(APIView):
    """GET /api/v1/research/runs/

    Lists historical research runs with optional session or scenario filtering.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ResearchRun.objects.all()

        session_id = request.query_params.get("session")
        if session_id:
            qs = qs.filter(session_id=session_id)

        scenario = request.query_params.get("scenario")
        if scenario:
            qs = qs.filter(scenario=scenario)

        limit = min(int(request.query_params.get("limit", 50)), 200)
        serializer = ResearchRunListSerializer(qs[:limit], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResearchRunDetailView(APIView):
    """GET /api/v1/research/runs/<run_id>/

    Retrieves complete run execution results including per-window evaluations.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, run_id):
        try:
            run = ResearchRun.objects.get(run_id=run_id)
        except ResearchRun.DoesNotExist:
            return Response(
                {"detail": f"Research run '{run_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ResearchRunDetailSerializer(run)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResearchRunCompareView(APIView):
    """GET /api/v1/research/runs/compare/?run_ids=RUN-1,RUN-2

    Compares two or more research runs side-by-side, identifying engine and metric differences.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        run_ids_param = request.query_params.get("run_ids", "")
        raw_ids = [rid.strip() for rid in run_ids_param.split(",") if rid.strip()]
        run_ids = list(dict.fromkeys(raw_ids))

        if len(run_ids) < 2:
            return Response(
                {"detail": "At least two distinct run_ids required for comparison (e.g. ?run_ids=ID1,ID2)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        runs = list(ResearchRun.objects.filter(run_id__in=run_ids))
        if len(runs) < len(run_ids):
            found_ids = {r.run_id for r in runs}
            missing = set(run_ids) - found_ids
            return Response(
                {"detail": f"Runs not found: {list(missing)}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Build structured comparison
        comparison_runs = []
        for r in runs:
            comparison_runs.append({
                "run_id": r.run_id,
                "session_id": r.session_id,
                "scenario": r.scenario,
                "dataset_id": r.dataset_id,
                "dataset_version": r.dataset_version,
                "engine_version": r.engine_version,
                "code_revision": r.code_revision,
                "created_at": r.created_at.isoformat(),
                "total_windows_evaluated": r.total_windows_evaluated,
                "execution_duration_sec": r.execution_duration_sec,
                "throughput_samples_per_sec": r.throughput_samples_per_sec,
                "mean_confidence": r.mean_confidence,
                "mean_sqi": r.mean_sqi,
                "abstention_rate_pct": r.abstention_rate_pct,
                "state_breakdown": r.state_breakdown,
                "dominant_factors_summary": r.dominant_factors_summary[:5],
            })

        # Identify differences in environment/engine/dataset
        version_differences = {
            "dataset_version_diff": len({r["dataset_version"] for r in comparison_runs}) > 1,
            "engine_version_diff": len({r["engine_version"] for r in comparison_runs}) > 1,
            "scenario_diff": len({r["scenario"] for r in comparison_runs}) > 1,
        }

        return Response({
            "compared_run_count": len(comparison_runs),
            "version_differences": version_differences,
            "runs": comparison_runs,
        }, status=status.HTTP_200_OK)


class ResearchExportView(APIView):
    """GET /api/v1/research/export/<session_id>/?format=csv|json

    Exports session telemetry and existing engine execution evaluation.
    """
    permission_classes = [IsAuthenticated]
    renderer_classes = [PassthroughCSVRenderer, JSONRenderer]

    def get(self, request, session_id):
        export_format = request.query_params.get("format", "csv").lower()
        records = registry.stream_session_records(session_id=session_id, downsample_factor=1)

        # Check if there is an existing run for this session to append classifications
        latest_run = ResearchRun.objects.filter(session_id=session_id).first()
        window_map = {}
        if latest_run and latest_run.window_outputs:
            for w in latest_run.window_outputs:
                window_map[w["timestamp"]] = w

        if export_format == "json":
            export_data = {
                "session_id": session_id,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "data_source": "SYNTHETIC",
                "total_observations": len(records),
                "latest_engine_run": latest_run.run_id if latest_run else None,
                "records": [
                    {
                        **r,
                        "evaluated_state": window_map.get(r["timestamp"], {}).get("state"),
                        "engine_confidence": window_map.get(r["timestamp"], {}).get("confidence"),
                        "engine_sqi": window_map.get(r["timestamp"], {}).get("sqi"),
                    }
                    for r in records
                ]
            }
            response = HttpResponse(json.dumps(export_data, indent=2), content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="{session_id}_research_export.json"'
            return response

        # Default CSV export
        output = io.StringIO()
        fieldnames = [
            "timestamp", "participant_id", "session_id", "scenario",
            "heart_rate", "rr_interval", "spo2", "skin_temperature",
            "activity_level", "accel_z", "external_g_load", "mission_phase",
            "evaluated_state", "engine_confidence", "engine_sqi"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for r in records:
            w_res = window_map.get(r["timestamp"], {})
            rr = r.get("rr_interval")
            if isinstance(rr, list):
                rr = ";".join(str(x) for x in rr)

            writer.writerow({
                "timestamp": r.get("timestamp"),
                "participant_id": r.get("participant_id"),
                "session_id": r.get("session_id"),
                "scenario": r.get("scenario"),
                "heart_rate": r.get("heart_rate") if r.get("heart_rate") is not None else "",
                "rr_interval": rr if rr is not None else "",
                "spo2": "",
                "skin_temperature": "",
                "activity_level": r.get("activity_level"),
                "accel_z": r.get("accel_z"),
                "external_g_load": r.get("external_g_load"),
                "mission_phase": r.get("mission_phase"),
                "evaluated_state": w_res.get("state", ""),
                "engine_confidence": w_res.get("confidence", ""),
                "engine_sqi": w_res.get("sqi", ""),
            })

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{session_id}_research_export.csv"'
        return response
