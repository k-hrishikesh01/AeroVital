"""Research Services for AeroVital.

Provides dataset registry access, selective streaming, path traversal security,
and execution bridging to the unmodified AeroVital Core Intelligence Engine.
"""

import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from rest_framework.exceptions import NotFound, ValidationError

logger = logging.getLogger(__name__)

# Security: Strict validation regexes preventing path traversal or malformed identifiers
RE_SESSION_ID = re.compile(r"^SYN-S\d{3}$")
RE_PARTICIPANT_ID = re.compile(r"^SYN-P\d{3}$")
RE_SCENARIO = re.compile(r"^[A-Z0-9_]{3,50}$")


class DatasetRegistry:
    """Fixed, server-controlled dataset registry for synthetic research datasets."""

    def __init__(self):
        # Resolve dataset root safely relative to django-backend or repository root
        base_dir = Path(settings.BASE_DIR)
        repo_root = base_dir.parent if base_dir.name == "django-backend" else base_dir
        self.dataset_dir = repo_root / "research" / "datasets" / "aerovital_synthetic_v1"

        self._manifest_cache: Optional[Dict[str, Any]] = None
        self._participants_cache: Optional[List[Dict[str, Any]]] = None
        self._sessions_cache: Optional[List[Dict[str, Any]]] = None

    def _ensure_dir_exists(self):
        if not self.dataset_dir.exists():
            raise NotFound(f"Research dataset not found at registry path: {self.dataset_dir}")

    def get_manifest(self) -> Dict[str, Any]:
        """Load and cache dataset manifest."""
        if self._manifest_cache is None:
            self._ensure_dir_exists()
            manifest_file = self.dataset_dir / "dataset_manifest.json"
            if not manifest_file.exists():
                raise NotFound("Dataset manifest not found.")
            with open(manifest_file, "r", encoding="utf-8") as f:
                self._manifest_cache = json.load(f)
        return self._manifest_cache

    def get_participants(self) -> List[Dict[str, Any]]:
        """Load and cache synthetic participants list."""
        if self._participants_cache is None:
            self._ensure_dir_exists()
            p_file = self.dataset_dir / "participants.json"
            if not p_file.exists():
                raise NotFound("Participants metadata not found.")
            with open(p_file, "r", encoding="utf-8") as f:
                self._participants_cache = json.load(f)
        return self._participants_cache

    def get_participant_by_id(self, participant_id: str) -> Dict[str, Any]:
        """Look up a single participant by ID with strict validation."""
        if not RE_PARTICIPANT_ID.match(participant_id):
            raise ValidationError(f"Invalid participant identifier format: '{participant_id}'")
        for p in self.get_participants():
            if p["pilot_id"] == participant_id:
                return p
        raise NotFound(f"Participant '{participant_id}' not found.")

    def get_sessions(self, scenario: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load session metadata with optional scenario filtering."""
        if self._sessions_cache is None:
            self._ensure_dir_exists()
            s_file = self.dataset_dir / "sessions.json"
            if not s_file.exists():
                raise NotFound("Sessions metadata not found.")
            with open(s_file, "r", encoding="utf-8") as f:
                self._sessions_cache = json.load(f)

        if scenario:
            if not RE_SCENARIO.match(scenario):
                raise ValidationError(f"Invalid scenario parameter format: '{scenario}'")
            return [s for s in self._sessions_cache if s["scenario"] == scenario]
        return self._sessions_cache

    def get_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Look up session metadata by ID with strict validation."""
        if not RE_SESSION_ID.match(session_id):
            raise ValidationError(f"Invalid session identifier format: '{session_id}'")
        for s in self.get_sessions():
            if s["session_id"] == session_id:
                return s
        raise NotFound(f"Session '{session_id}' not found in dataset registry.")

    def stream_session_records(
        self,
        session_id: str,
        downsample_factor: int = 1,
    ) -> List[Dict[str, Any]]:
        """Selectively stream records for a single session without loading whole dataset.
        
        Args:
            session_id: Validated session ID (e.g. 'SYN-S001')
            downsample_factor: Integer downsample factor (1 = full 1 Hz, 5 = 1 per 5s, etc.)
            
        Returns:
            List of downsampled observation dictionaries.
        """
        # Validate session ID format to prevent path traversal
        if not RE_SESSION_ID.match(session_id):
            raise ValidationError(f"Invalid session identifier format: '{session_id}'")
        
        # Verify session exists in registry and retrieve expected observation count
        session_meta = self.get_session_by_id(session_id)
        total_observations = session_meta.get("total_observations") or session_meta.get("duration_sec") or 3600

        jsonl_gz_path = self.dataset_dir / "synthetic_physiological_dataset.jsonl.gz"
        jsonl_path = self.dataset_dir / "synthetic_physiological_dataset.jsonl"

        if jsonl_gz_path.exists():
            import gzip
            file_opener = lambda: gzip.open(jsonl_gz_path, "rt", encoding="utf-8")
        elif jsonl_path.exists():
            file_opener = lambda: open(jsonl_path, "r", encoding="utf-8")
        else:
            raise NotFound("Synthetic JSONL dataset file not found.")

        factor = max(1, min(60, int(downsample_factor)))
        records: List[Dict[str, Any]] = []
        matching_count = 0

        # Stream lines selectively
        with file_opener() as f:
            for line in f:
                if not line.strip():
                    continue
                # Quick string check before full json parse for fast streaming
                if f'"{session_id}"' not in line:
                    if records:
                        # Since sessions are sequentially contiguous, if we already collected records
                        # and no longer see session_id, we can safely break early
                        break
                    continue

                rec = json.loads(line)
                if rec.get("session_id") == session_id:
                    matching_count += 1
                    # Downsample selection: always include first, stride points, and terminal observation
                    if (matching_count - 1) % factor == 0 or matching_count == total_observations:
                        records.append(rec)

        if not records:
            raise NotFound(f"No records found for session '{session_id}'.")

        return records


# Singleton dataset registry
registry = DatasetRegistry()


class EngineExecutionService:
    """Bridges Django research requests to the framework-independent AeroVitalPipeline."""

    @staticmethod
    def execute_session(
        session_id: str,
        user: Any = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Execute AeroVital Core Intelligence Engine on a synthetic session.
        
        Executes without altering algorithms, capturing all per-window classifications,
        confidence, SQI, and abstentions, and persists the run into ResearchRun.
        """
        from backend.core.pipeline.pipeline import AeroVitalPipeline
        from backend.core.schemas.baseline import PilotBaseline
        from backend.core.schemas.context import MissionPhase, OperationalContext
        from backend.core.schemas.telemetry import TelemetrySample
        from research.models import ResearchRun

        # 1. Retrieve session and participant metadata
        session_meta = registry.get_session_by_id(session_id)
        participant_id = session_meta["participant_id"]
        participant_meta = registry.get_participant_by_id(participant_id)
        manifest = registry.get_manifest()

        # 2. Build PilotBaseline profile
        cal_ts = datetime.fromisoformat(participant_meta["calibration_timestamp"])
        baseline = PilotBaseline(
            pilot_id=participant_meta["pilot_id"],
            baseline_version=participant_meta["baseline_version"],
            resting_heart_rate=participant_meta["resting_heart_rate"],
            baseline_rmssd=participant_meta["baseline_rmssd"],
            baseline_sdnn=participant_meta["baseline_sdnn"],
            baseline_mean_rr=participant_meta["baseline_mean_rr"],
            created_at=cal_ts,
        )

        # 3. Stream all 3,600 raw records (downsample_factor=1 for engine execution)
        raw_records = registry.stream_session_records(session_id=session_id, downsample_factor=1)

        # 4. Instantiate pipeline
        pipeline = AeroVitalPipeline(baseline=baseline)

        # 5. Execute pipeline sample-by-sample
        start_time = time.time()
        window_outputs: List[Dict[str, Any]] = []
        state_counts: Dict[str, int] = {}
        confidences: List[float] = []
        sqis: List[float] = []
        dominant_factors_counter: Dict[str, int] = {}

        for r in raw_records:
            ts = datetime.fromisoformat(r["timestamp"])
            s = TelemetrySample(
                timestamp=ts,
                heart_rate=r["heart_rate"],
                rr_interval=r["rr_interval"],
                accel_x=r["accel_x"],
                accel_y=r["accel_y"],
                accel_z=r["accel_z"],
            )
            ctx = OperationalContext(
                timestamp=ts,
                mission_phase=MissionPhase(r["mission_phase"]) if r.get("mission_phase") else None,
                external_g_load=r.get("external_g_load"),
                flight_duration_sec=r.get("flight_duration_sec"),
            )

            res = pipeline.process_sample(s, context=ctx)
            if res is not None:
                st = res.fatigue_state.value
                state_counts[st] = state_counts.get(st, 0) + 1
                confidences.append(res.confidence)
                sqis.append(res.overall_sqi)

                for f in res.dominant_factors:
                    dominant_factors_counter[f] = dominant_factors_counter.get(f, 0) + 1

                window_outputs.append({
                    "timestamp": res.timestamp.isoformat(),
                    "state": st,
                    "confidence": round(res.confidence, 3),
                    "sqi": round(res.overall_sqi, 3),
                    "dominant_factors": res.dominant_factors,
                })

        duration = time.time() - start_time
        total_windows = len(window_outputs)
        abstentions = state_counts.get("INSUFFICIENT_DATA", 0)
        abstention_rate = round(100.0 * abstentions / max(1, total_windows), 2)
        throughput = round(len(raw_records) / max(0.001, duration), 1)

        # State percentages
        state_breakdown = {
            st: {
                "count": count,
                "percentage": round(100.0 * count / max(1, total_windows), 2)
            }
            for st, count in sorted(state_counts.items())
        }

        # Top dominant factors summary
        top_factors = sorted(
            [{"factor": f, "count": c} for f, c in dominant_factors_counter.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:8]

        # 6. Generate immutable run ID
        run_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

        # 7. Persist to isolated ResearchRun table
        research_run = ResearchRun.objects.create(
            run_id=run_id,
            dataset_id=manifest.get("dataset_id", "aerovital-synthetic-v1"),
            dataset_version=manifest.get("schema_version", "1.0.0"),
            dataset_checksum=(
                manifest.get("files", {}).get("synthetic_physiological_dataset.jsonl.gz", {}).get("sha256")
                or manifest.get("files", {}).get("synthetic_physiological_dataset.jsonl", {}).get("sha256", "")
            ),
            generator_version=manifest.get("generator_version", "1.0.0"),
            engine_version="1.0.0",
            code_revision="715e784",
            random_seed=manifest.get("random_seed", 42),
            session_id=session_id,
            participant_id=participant_id,
            scenario=session_meta["scenario"],
            total_samples_processed=len(raw_records),
            total_windows_evaluated=total_windows,
            execution_duration_sec=round(duration, 3),
            throughput_samples_per_sec=throughput,
            mean_confidence=round(float(sum(confidences) / len(confidences)), 3) if confidences else None,
            mean_sqi=round(float(sum(sqis) / len(sqis)), 3) if sqis else None,
            abstention_rate_pct=abstention_rate,
            state_breakdown=state_breakdown,
            dominant_factors_summary=top_factors,
            window_outputs=window_outputs,
            created_by=user if (user and user.is_authenticated) else None,
            notes=notes,
        )

        return {
            "run_id": research_run.run_id,
            "session_id": session_id,
            "participant_id": participant_id,
            "scenario": session_meta["scenario"],
            "dataset_id": research_run.dataset_id,
            "engine_version": research_run.engine_version,
            "total_samples_processed": research_run.total_samples_processed,
            "total_windows_evaluated": research_run.total_windows_evaluated,
            "execution_duration_sec": research_run.execution_duration_sec,
            "throughput_samples_per_sec": research_run.throughput_samples_per_sec,
            "mean_confidence": research_run.mean_confidence,
            "mean_sqi": research_run.mean_sqi,
            "abstention_rate_pct": research_run.abstention_rate_pct,
            "state_breakdown": research_run.state_breakdown,
            "dominant_factors_summary": research_run.dominant_factors_summary,
            "window_outputs": window_outputs,
            "created_at": research_run.created_at.isoformat(),
            "disclaimer": research_run.disclaimer,
        }
