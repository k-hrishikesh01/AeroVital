"""
AeroVital Telemetry Ingestion & Core Orchestration Service.

Bridges Django API and persistence layer with the verified AeroVital Core Engine.
Orchestrates:
1. Core validation (TelemetryValidator)
2. Telemetry persistence (raw & parsed)
3. Pipeline window buffering & execution (AeroVitalPipeline)
4. Result persistence (SignalQuality, FeatureWindow, StateEstimate)
5. Alert dispatching based on Core results
"""

from datetime import datetime, timezone as dt_timezone
from typing import Any, Dict, List, Optional, Sequence, Union
import logging

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from backend.core.schemas.telemetry import TelemetrySample
from backend.core.schemas.context import OperationalContext, MissionPhase
from backend.core.schemas.result import FatigueEstimationResult, FatigueState
from backend.core.schemas.quality import QualityAssessment
from backend.core.schemas.features import FeatureVector
from backend.core.pipeline.pipeline import AeroVitalPipeline
from backend.core.validation.validator import TelemetryValidator
from backend.core.validation.exceptions import SignalValidationError

from pilots.models import Pilot
from devices.models import Device
from missions.models import Mission
from telemetry.models import Telemetry, SignalQuality, FeatureWindow
from intelligence.models import Baseline, StateEstimate
from alerts.models import Alert

logger = logging.getLogger(__name__)


class PipelineSessionManager:
    """Manages stateful AeroVitalPipeline instances per active mission session."""

    def __init__(self):
        self._cache: Dict[str, AeroVitalPipeline] = {}

    def get_session_key(self, mission: Optional[Mission], pilot: Optional[Pilot]) -> str:
        if mission and mission.id:
            return f"mission:{mission.id}"
        if pilot and pilot.id:
            return f"pilot:{pilot.id}"
        return "default"

    def get_pipeline(
        self,
        mission: Optional[Mission] = None,
        pilot: Optional[Pilot] = None,
        before_timestamp: Optional[datetime] = None,
    ) -> AeroVitalPipeline:
        key = self.get_session_key(mission, pilot)
        if key in self._cache:
            pipeline = self._cache[key]
        else:
            pipeline = AeroVitalPipeline()
            # Hydrate baseline if available
            target_pilot = pilot or (mission.pilot if mission else None)
            if target_pilot:
                active_baseline = Baseline.objects.filter(
                    pilot=target_pilot,
                    is_active=True,
                ).first()
                if active_baseline:
                    pipeline.set_baseline(active_baseline.to_core())

            # Hydrate recent window samples from DB if buffer is empty
            target_mission = mission
            target_pilot = pilot or (mission.pilot if mission else None)
            
            qs = None
            if target_mission:
                qs = Telemetry.objects.filter(mission=target_mission)
            elif target_pilot:
                qs = Telemetry.objects.filter(pilot=target_pilot, mission__isnull=True)
            elif key == "default":
                qs = Telemetry.objects.filter(mission__isnull=True, pilot__isnull=True)

            if qs is not None:
                buffer_limit = max(50, int(pipeline.window_buffer.config.window_duration_sec * 2))
                if before_timestamp:
                    qs = qs.filter(timestamp__lt=before_timestamp)
                recent_qs = qs.order_by("-timestamp")[:buffer_limit]
                recent_list = list(reversed(recent_qs))
                for record in recent_list:
                    try:
                        sample = record.to_core_sample()
                        pipeline.window_buffer.add_sample(sample)
                        pipeline._last_sample_timestamp = sample.timestamp
                    except Exception as err:
                        logger.warning("Failed hydrating sample into pipeline buffer: %s", err)

            self._cache[key] = pipeline

        # Keep baseline updated if changed
        target_pilot = pilot or (mission.pilot if mission else None)
        if target_pilot:
            active_baseline = Baseline.objects.filter(
                pilot=target_pilot,
                is_active=True,
            ).first()
            if active_baseline:
                pipeline.set_baseline(active_baseline.to_core())
            else:
                pipeline.set_baseline(None)

        return pipeline

    def reset_session(self, mission: Optional[Mission] = None, pilot: Optional[Pilot] = None) -> None:
        key = self.get_session_key(mission, pilot)
        if key in self._cache:
            self._cache[key].reset()


pipeline_manager = PipelineSessionManager()
validator = TelemetryValidator()


def parse_and_validate_telemetry_dict(data: Dict[str, Any]) -> TelemetrySample:
    """Validate incoming raw dictionary against Core TelemetryValidator.
    
    Raises rest_framework.exceptions.ValidationError on physiological or schema violations.
    """
    # Normalize timestamp
    raw_ts = data.get("timestamp")
    if not raw_ts:
        raise ValidationError({"timestamp": "Timestamp is required."})

    if isinstance(raw_ts, str):
        try:
            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
        except ValueError as err:
            raise ValidationError({"timestamp": f"Invalid ISO 8601 timestamp: {err}"})
    elif isinstance(raw_ts, datetime):
        ts = raw_ts
    else:
        raise ValidationError({"timestamp": "Invalid timestamp format."})

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt_timezone.utc)

    # Normalize rr_interval (scalar float or list of floats)
    raw_rr = data.get("rr_interval")
    normalized_rr: Optional[Union[float, List[float]]] = None
    if raw_rr is not None:
        if isinstance(raw_rr, (int, float)):
            normalized_rr = float(raw_rr)
        elif isinstance(raw_rr, list):
            try:
                normalized_rr = [float(x) for x in raw_rr]
            except (ValueError, TypeError) as err:
                raise ValidationError({"rr_interval": f"All elements in rr_interval must be floats: {err}"})
        else:
            raise ValidationError({"rr_interval": "rr_interval must be a float or list of floats."})

    try:
        sample = TelemetrySample(
            timestamp=ts,
            heart_rate=float(data["heart_rate"]) if data.get("heart_rate") is not None else None,
            rr_interval=normalized_rr,
            spo2=float(data["spo2"]) if data.get("spo2") is not None else None,
            skin_temperature=float(data["skin_temperature"]) if data.get("skin_temperature") is not None else None,
            activity_level=data.get("activity_level"),
            steps=int(data["steps"]) if data.get("steps") is not None else None,
            accel_x=float(data["accel_x"]) if data.get("accel_x") is not None else None,
            accel_y=float(data["accel_y"]) if data.get("accel_y") is not None else None,
            accel_z=float(data["accel_z"]) if data.get("accel_z") is not None else None,
            battery_level=float(data["battery_level"]) if data.get("battery_level") is not None else None,
            raw_payload=data.get("raw_payload") or {},
        )
    except Exception as err:
        raise ValidationError({"detail": f"Schema construction failed: {err}"})

    # Validate against verified Core physiological and structural rules
    try:
        validated_sample = validator.validate_sample(sample)
    except SignalValidationError as err:
        raise ValidationError({"telemetry_validation_error": str(err)})

    return validated_sample


def build_operational_context(mission: Optional[Mission], timestamp: datetime) -> Optional[OperationalContext]:
    """Extract operational flight context from Mission if active."""
    if not mission:
        return None

    phase_str = (mission.current_phase or "CRUISE").upper()
    try:
        phase = MissionPhase(phase_str)
    except ValueError:
        phase = MissionPhase.CRUISE

    flight_duration = None
    if mission.start_time:
        duration_delta = timestamp - mission.start_time
        flight_duration = max(0.0, duration_delta.total_seconds())

    return OperationalContext(
        timestamp=timestamp,
        mission_phase=phase,
        external_g_load=mission.external_g_load or 1.0,
        flight_duration_sec=flight_duration,
        metadata=mission.environment or {},
    )


def ingest_telemetry_sample(
    data: Dict[str, Any],
    pilot: Optional[Pilot] = None,
    device: Optional[Device] = None,
    mission: Optional[Mission] = None,
) -> Dict[str, Any]:
    """Ingest a single telemetry sample, run through Core pipeline, and persist outputs.
    
    Returns:
        Dict with keys:
            - telemetry: Telemetry instance
            - status: 'evaluated' or 'accumulating'
            - estimate: StateEstimate instance (or None)
            - quality: SignalQuality instance (or None)
            - alert: Alert instance (or None)
    """
    # 1. Validate sample using Core validator
    core_sample = parse_and_validate_telemetry_dict(data)

    # Resolve associations if passed in payload IDs
    if not pilot and data.get("pilot"):
        pilot = Pilot.objects.filter(id=data["pilot"]).first()
    if not device and data.get("device"):
        device = Device.objects.filter(id=data["device"]).first()
    if not mission and data.get("mission"):
        mission = Mission.objects.filter(id=data["mission"]).first()

    # Link device to pilot if known
    if device and not pilot and device.pilot:
        pilot = device.pilot

    # Link mission to pilot if known
    if mission and not pilot and mission.pilot:
        pilot = mission.pilot

    # 2. Obtain pipeline session and verify temporal ordering
    pipeline = pipeline_manager.get_pipeline(
        mission=mission,
        pilot=pilot,
        before_timestamp=core_sample.timestamp,
    )

    if pipeline._last_sample_timestamp is not None:
        if core_sample.timestamp <= pipeline._last_sample_timestamp:
            raise ValidationError({
                "timestamp": f"Timestamp {core_sample.timestamp} must be strictly greater than previous sample timestamp {pipeline._last_sample_timestamp}."
            })

    # 3. Persist raw Telemetry record
    telemetry_record = Telemetry.objects.create(
        pilot=pilot,
        device=device,
        mission=mission,
        timestamp=core_sample.timestamp,
        heart_rate=core_sample.heart_rate,
        rr_interval=core_sample.rr_interval,
        spo2=core_sample.spo2,
        skin_temperature=core_sample.skin_temperature,
        activity_level=core_sample.activity_level,
        steps=core_sample.steps,
        accel_x=core_sample.accel_x,
        accel_y=core_sample.accel_y,
        accel_z=core_sample.accel_z,
        battery_level=core_sample.battery_level,
        raw_payload=core_sample.raw_payload or {},
    )

    if device:
        device.last_seen_at = timezone.now()
        device.save(update_fields=["last_seen_at"])

    # 4. Process sample through verified Core pipeline
    context = build_operational_context(mission, core_sample.timestamp)
    result: Optional[FatigueEstimationResult] = pipeline.process_sample(core_sample, context=context)

    estimate_record: Optional[StateEstimate] = None
    quality_record: Optional[SignalQuality] = None
    window_record: Optional[FeatureWindow] = None
    alert_record: Optional[Alert] = None

    if result is not None:
        # Buffer window is ready and was evaluated by Core!
        snapshot = pipeline.window_buffer.snapshot()
        if snapshot is not None:
            # Stage 3 Quality
            quality: QualityAssessment = pipeline.quality_assessor.assess_window(snapshot.samples)
            channels_dict = {
                name: {
                    "sqi_score": ch.sqi_score,
                    "is_usable": ch.is_usable,
                    "missing_sample_ratio": ch.missing_sample_ratio,
                    "motion_artifact_detected": ch.motion_artifact_detected,
                    "notes": ch.notes,
                }
                for name, ch in quality.channels.items()
            }
            quality_record = SignalQuality.objects.create(
                pilot=pilot,
                device=device,
                mission=mission,
                timestamp=quality.timestamp,
                overall_sqi=quality.overall_sqi,
                is_telemetry_acceptable=quality.is_telemetry_acceptable,
                motion_corruption_index=quality.motion_corruption_index,
                channels=channels_dict,
            )

            # Stage 5 Features
            raw_features: FeatureVector = pipeline.feature_extractor.extract_features(snapshot)
            normalized_features = pipeline.baseline_normalizer.normalize(
                features=raw_features,
                baseline=pipeline.baseline,
            )
            window_record = FeatureWindow.objects.create(
                pilot=pilot,
                device=device,
                mission=mission,
                window_start=normalized_features.window_start,
                window_end=normalized_features.window_end,
                window_duration_sec=normalized_features.window_duration_sec,
                mean_hr=normalized_features.hr_features.mean_hr,
                min_hr=normalized_features.hr_features.min_hr,
                max_hr=normalized_features.hr_features.max_hr,
                hr_std=normalized_features.hr_features.hr_std,
                mean_rr_ms=normalized_features.hrv_features.mean_rr_ms,
                sdnn_ms=normalized_features.hrv_features.sdnn_ms,
                rmssd_ms=normalized_features.hrv_features.rmssd_ms,
                pnn50_percent=normalized_features.hrv_features.pnn50_percent,
                mean_magnitude=normalized_features.motion_features.mean_magnitude,
                activity_intensity=normalized_features.motion_features.activity_intensity,
                baseline_available=normalized_features.baseline_features.baseline_available,
                hr_deviation_from_baseline=normalized_features.baseline_features.hr_deviation_from_baseline,
                hrv_rmssd_ratio_to_baseline=normalized_features.baseline_features.hrv_rmssd_ratio_to_baseline,
                features_payload=normalized_features.model_dump(mode="json"),
            )

        # Stage 7 & 8 State Estimate Persistence
        evidence_dict = {}
        if hasattr(pipeline.estimator, "_latest_rule_trace"):
            evidence_dict = getattr(pipeline.estimator, "_latest_rule_trace", {})

        estimate_record = StateEstimate.from_core(
            result=result,
            pilot=pilot,
            mission=mission,
            feature_window=window_record,
            evidence=evidence_dict,
        )

        # Alert Generation based on Core result semantics
        if result.fatigue_state == FatigueState.FATIGUE:
            alert_record = Alert.objects.create(
                pilot=pilot,
                mission=mission,
                state_estimate=estimate_record,
                timestamp=result.timestamp,
                alert_type="FATIGUE_WARNING",
                severity=Alert.Severity.WARNING if result.confidence >= 0.70 else Alert.Severity.INFO,
                message=f"Fatigue state detected (Confidence: {result.confidence:.2f}). Factors: {', '.join(result.dominant_factors)}",
                trigger_state=result.fatigue_state.value,
                confidence=result.confidence,
            )
        elif result.fatigue_state == FatigueState.ELEVATED_WORKLOAD:
            alert_record = Alert.objects.create(
                pilot=pilot,
                mission=mission,
                state_estimate=estimate_record,
                timestamp=result.timestamp,
                alert_type="WORKLOAD_ADVISORY",
                severity=Alert.Severity.INFO,
                message=f"Elevated workload detected (Confidence: {result.confidence:.2f}). Factors: {', '.join(result.dominant_factors)}",
                trigger_state=result.fatigue_state.value,
                confidence=result.confidence,
            )
        elif result.overall_sqi < 0.50:
            alert_record = Alert.objects.create(
                pilot=pilot,
                mission=mission,
                state_estimate=estimate_record,
                timestamp=result.timestamp,
                alert_type="SIGNAL_QUALITY_DEGRADED",
                severity=Alert.Severity.WARNING,
                message=f"Sensor signal quality degraded (SQI: {result.overall_sqi:.2f}). Verify sensor placement.",
                trigger_state=result.fatigue_state.value,
                confidence=result.confidence,
            )

    return {
        "telemetry": telemetry_record,
        "status": "evaluated" if result is not None else "accumulating",
        "estimate": estimate_record,
        "quality": quality_record,
        "alert": alert_record,
    }


def evaluate_batch_window_samples(
    samples_data: Sequence[Dict[str, Any]],
    pilot: Optional[Pilot] = None,
    device: Optional[Device] = None,
    mission: Optional[Mission] = None,
) -> Dict[str, Any]:
    """Directly evaluate a complete window batch of samples through the Core."""
    validated_samples: List[TelemetrySample] = []
    for s_dict in samples_data:
        validated_samples.append(parse_and_validate_telemetry_dict(s_dict))

    pipeline = pipeline_manager.get_pipeline(mission=mission, pilot=pilot)
    context = None
    if mission and validated_samples:
        context = build_operational_context(mission, validated_samples[-1].timestamp)

    result = pipeline.process_window_samples(validated_samples, context=context)

    # Persist the latest telemetry record
    telemetry_records = []
    for s in validated_samples:
        rec = Telemetry.objects.create(
            pilot=pilot,
            device=device,
            mission=mission,
            timestamp=s.timestamp,
            heart_rate=s.heart_rate,
            rr_interval=s.rr_interval,
            spo2=s.spo2,
            skin_temperature=s.skin_temperature,
            activity_level=s.activity_level,
            steps=s.steps,
            accel_x=s.accel_x,
            accel_y=s.accel_y,
            accel_z=s.accel_z,
            battery_level=s.battery_level,
            raw_payload=s.raw_payload or {},
        )
        telemetry_records.append(rec)

    estimate_record = StateEstimate.from_core(
        result=result,
        pilot=pilot,
        mission=mission,
        feature_window=None,
    )

    return {
        "status": "evaluated",
        "telemetry_count": len(telemetry_records),
        "estimate": estimate_record,
    }
