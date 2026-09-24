"""Signal Quality Assessment Engine for AeroVital Core.

Evaluates how trustworthy incoming telemetry signals are for downstream processing.
This layer:
- DOES NOT determine fatigue or calculate fatigue scores.
- DOES NOT assign fatigue states.
- DOES NOT use medical thresholds or invent clinical cutoffs.
- Operates strictly on measurable engineering properties (completeness, jitter, motion corruption).
- Distinguishes channel unavailability from poor quality and insufficient history.
- Never fabricates or imputes missing physiological measurements.
"""

from datetime import datetime, timezone
from typing import Dict, Optional, Sequence

from backend.core.schemas.telemetry import TelemetrySample
from backend.core.schemas.quality import ChannelQuality, QualityAssessment
from backend.core.quality.rules import (
    QualityConfig,
    evaluate_motion_corruption,
    evaluate_window_motion,
    evaluate_sampling_continuity,
)


class SignalQualityAssessor:
    """Assesses signal trustworthiness per-channel and compositely across available telemetry streams."""

    def __init__(self, config: Optional[QualityConfig] = None):
        self.config = config or QualityConfig()

    def assess_sample(
        self,
        sample: TelemetrySample,
        previous_timestamp: Optional[datetime] = None,
    ) -> QualityAssessment:
        """Assess the quality of an individual telemetry sample.
        
        Args:
            sample: The validated TelemetrySample.
            previous_timestamp: Optional previous observation timestamp for continuity check.
            
        Returns:
            QualityAssessment containing channel-level and aggregate SQI.
        """
        # 1. Motion artifact evaluation from accelerometer
        motion_index, motion_detected = evaluate_motion_corruption(sample, self.config)

        # 2. Timing jitter check if predecessor timestamp provided
        timing_sqi = 1.0
        missing_ratio = 0.0
        if previous_timestamp is not None:
            delta = (sample.timestamp - previous_timestamp).total_seconds()
            expected = self.config.expected_sampling_interval_sec
            if delta > expected * self.config.gap_multiplier_for_missingness:
                missing_ratio = min(1.0, (delta - expected) / max(0.1, delta))
                timing_sqi = max(0.0, 1.0 - missing_ratio)

        # 3. Assess individual channels
        channels: Dict[str, ChannelQuality] = {}

        # Heart Rate
        channels["heart_rate"] = self._assess_heart_rate(
            sample=sample,
            motion_index=motion_index,
            motion_detected=motion_detected,
            timing_sqi=timing_sqi,
            missing_ratio=missing_ratio,
        )

        # RR Interval
        channels["rr_interval"] = self._assess_rr_interval(
            sample=sample,
            motion_index=motion_index,
            motion_detected=motion_detected,
            timing_sqi=timing_sqi,
            missing_ratio=missing_ratio,
        )

        # Accelerometer
        channels["accelerometer"] = self._assess_accelerometer(
            sample=sample,
            timing_sqi=timing_sqi,
            missing_ratio=missing_ratio,
        )

        # SpO2
        channels["spo2"] = self._assess_spo2(
            sample=sample,
            motion_index=motion_index,
            motion_detected=motion_detected,
            timing_sqi=timing_sqi,
            missing_ratio=missing_ratio,
        )

        # Skin Temperature
        channels["skin_temperature"] = self._assess_skin_temperature(
            sample=sample,
            timing_sqi=timing_sqi,
            missing_ratio=missing_ratio,
        )

        # 4. Composite Quality Aggregation
        overall_sqi, is_acceptable = self._aggregate_quality(channels)

        return QualityAssessment(
            timestamp=sample.timestamp,
            overall_sqi=overall_sqi,
            channels=channels,
            motion_corruption_index=motion_index,
            is_telemetry_acceptable=is_acceptable,
        )

    def assess_window(
        self,
        samples: Sequence[TelemetrySample],
    ) -> QualityAssessment:
        """Assess the signal quality across a temporal sequence of samples.
        
        Args:
            samples: Ordered sequence of TelemetrySample observations.
            
        Returns:
            QualityAssessment reflecting window-level completeness, jitter, and motion.
        """
        if not samples:
            now = datetime.now(timezone.utc)
            return QualityAssessment(
                timestamp=now,
                overall_sqi=0.0,
                channels={},
                motion_corruption_index=0.0,
                is_telemetry_acceptable=False,
            )

        timestamp = samples[-1].timestamp
        sample_count = len(samples)

        # 1. Evaluate window motion from accelerometer samples
        motion_index, motion_detected = evaluate_window_motion(samples, self.config)

        # 2. Evaluate sampling continuity and jitter across timestamps
        timestamps = [s.timestamp for s in samples]
        timing_sqi, jitter_sec, missing_ratio = evaluate_sampling_continuity(timestamps, self.config)

        # Calculate expected sample count across window timespan
        total_expected_samples = max(
            sample_count,
            round((timestamps[-1] - timestamps[0]).total_seconds() / max(0.01, self.config.expected_sampling_interval_sec)) + 1
        )

        # 3. Channel assessments over the window
        channels: Dict[str, ChannelQuality] = {}

        # Heart Rate Window Assessment
        hr_present_count = sum(1 for s in samples if s.heart_rate is not None)
        channels["heart_rate"] = self._assess_channel_window(
            channel_name="heart_rate",
            present_count=hr_present_count,
            total_samples=sample_count,
            total_expected_samples=total_expected_samples,
            motion_index=motion_index,
            motion_detected=motion_detected,
            timing_sqi=timing_sqi,
            motion_susceptibility=self.config.window_motion_susceptibility_hr,
        )

        # RR Interval Window Assessment
        rr_present_count = sum(1 for s in samples if len(s.get_rr_intervals()) > 0)
        channels["rr_interval"] = self._assess_channel_window(
            channel_name="rr_interval",
            present_count=rr_present_count,
            total_samples=sample_count,
            total_expected_samples=total_expected_samples,
            motion_index=motion_index,
            motion_detected=motion_detected,
            timing_sqi=timing_sqi,
            motion_susceptibility=self.config.window_motion_susceptibility_rr,
        )

        # Accelerometer Window Assessment
        accel_present_count = sum(1 for s in samples if s.has_acceleration())
        channels["accelerometer"] = self._assess_channel_window(
            channel_name="accelerometer",
            present_count=accel_present_count,
            total_samples=sample_count,
            total_expected_samples=total_expected_samples,
            motion_index=0.0,  # Inertial sensors measure motion; motion does not corrupt their data completeness
            motion_detected=False,
            timing_sqi=timing_sqi,
            motion_susceptibility=0.0,
        )

        # SpO2 Window Assessment
        spo2_present_count = sum(1 for s in samples if s.spo2 is not None)
        channels["spo2"] = self._assess_channel_window(
            channel_name="spo2",
            present_count=spo2_present_count,
            total_samples=sample_count,
            total_expected_samples=total_expected_samples,
            motion_index=motion_index,
            motion_detected=motion_detected,
            timing_sqi=timing_sqi,
            motion_susceptibility=self.config.window_motion_susceptibility_spo2,
        )

        # Skin Temperature Window Assessment
        temp_present_count = sum(1 for s in samples if s.skin_temperature is not None)
        channels["skin_temperature"] = self._assess_channel_window(
            channel_name="skin_temperature",
            present_count=temp_present_count,
            total_samples=sample_count,
            total_expected_samples=total_expected_samples,
            motion_index=0.0,
            motion_detected=False,
            timing_sqi=timing_sqi,
            motion_susceptibility=0.0,
        )

        # 4. Aggregate
        overall_sqi, is_acceptable = self._aggregate_quality(channels)

        return QualityAssessment(
            timestamp=timestamp,
            overall_sqi=overall_sqi,
            channels=channels,
            motion_corruption_index=motion_index,
            is_telemetry_acceptable=is_acceptable,
        )

    # --- Single Sample Helpers ---

    def _assess_heart_rate(
        self,
        sample: TelemetrySample,
        motion_index: float,
        motion_detected: bool,
        timing_sqi: float,
        missing_ratio: float,
    ) -> ChannelQuality:
        if sample.heart_rate is None:
            return ChannelQuality(
                channel_name="heart_rate",
                sqi_score=0.0,
                is_usable=False,
                missing_sample_ratio=1.0,
                notes="UNAVAILABLE: Channel not provided in sample.",
            )

        # Base SQI degraded by motion corruption and timing jitter
        base_sqi = timing_sqi
        motion_penalty = motion_index * self.config.single_sample_motion_penalty_hr
        sqi = max(0.0, min(1.0, base_sqi - motion_penalty))
        usable = sqi >= self.config.min_channel_sqi_usable

        note = "ACCEPTABLE" if usable else "POOR_QUALITY: Motion corruption or timing irregularity."
        if motion_detected:
            note += " (Motion artifact detected)"

        return ChannelQuality(
            channel_name="heart_rate",
            sqi_score=round(sqi, 4),
            is_usable=usable,
            missing_sample_ratio=round(missing_ratio, 4),
            motion_artifact_detected=motion_detected,
            notes=note,
        )

    def _assess_rr_interval(
        self,
        sample: TelemetrySample,
        motion_index: float,
        motion_detected: bool,
        timing_sqi: float,
        missing_ratio: float,
    ) -> ChannelQuality:
        intervals = sample.get_rr_intervals()
        if not intervals:
            return ChannelQuality(
                channel_name="rr_interval",
                sqi_score=0.0,
                is_usable=False,
                missing_sample_ratio=1.0,
                notes="UNAVAILABLE: Channel not provided in sample.",
            )

        motion_penalty = motion_index * self.config.single_sample_motion_penalty_rr
        sqi = max(0.0, min(1.0, timing_sqi - motion_penalty))
        usable = sqi >= self.config.min_channel_sqi_usable

        note = "ACCEPTABLE" if usable else "POOR_QUALITY: Motion disturbance detected."
        if motion_detected:
            note += " (Motion artifact detected)"

        return ChannelQuality(
            channel_name="rr_interval",
            sqi_score=round(sqi, 4),
            is_usable=usable,
            missing_sample_ratio=round(missing_ratio, 4),
            motion_artifact_detected=motion_detected,
            notes=note,
        )

    def _assess_accelerometer(
        self,
        sample: TelemetrySample,
        timing_sqi: float,
        missing_ratio: float,
    ) -> ChannelQuality:
        if not sample.has_acceleration():
            return ChannelQuality(
                channel_name="accelerometer",
                sqi_score=0.0,
                is_usable=False,
                missing_sample_ratio=1.0,
                notes="UNAVAILABLE: Channel not provided in sample.",
            )

        # Accelerometer signal itself is intact if provided and timing is consistent
        sqi = timing_sqi
        usable = sqi >= self.config.min_channel_sqi_usable
        unit_str = self.config.accel_unit.value if hasattr(self.config.accel_unit, "value") else str(self.config.accel_unit).lower()
        if unit_str not in ("g", "m/s2", "m/s^2", "mps2"):
            note = "ACCEPTABLE (Unit unspecified: dynamic motion evaluation skipped)"
        else:
            note = "ACCEPTABLE" if usable else "POOR_QUALITY: Timing discontinuity."

        return ChannelQuality(
            channel_name="accelerometer",
            sqi_score=round(sqi, 4),
            is_usable=usable,
            missing_sample_ratio=round(missing_ratio, 4),
            motion_artifact_detected=False,
            notes=note,
        )

    def _assess_spo2(
        self,
        sample: TelemetrySample,
        motion_index: float,
        motion_detected: bool,
        timing_sqi: float,
        missing_ratio: float,
    ) -> ChannelQuality:
        if sample.spo2 is None:
            return ChannelQuality(
                channel_name="spo2",
                sqi_score=0.0,
                is_usable=False,
                missing_sample_ratio=1.0,
                notes="UNAVAILABLE: Channel not provided in sample.",
            )

        motion_penalty = motion_index * self.config.single_sample_motion_penalty_spo2
        sqi = max(0.0, min(1.0, timing_sqi - motion_penalty))
        usable = sqi >= self.config.min_channel_sqi_usable
        return ChannelQuality(
            channel_name="spo2",
            sqi_score=round(sqi, 4),
            is_usable=usable,
            missing_sample_ratio=round(missing_ratio, 4),
            motion_artifact_detected=motion_detected,
            notes="ACCEPTABLE" if usable else "POOR_QUALITY: Motion corruption.",
        )

    def _assess_skin_temperature(
        self,
        sample: TelemetrySample,
        timing_sqi: float,
        missing_ratio: float,
    ) -> ChannelQuality:
        if sample.skin_temperature is None:
            return ChannelQuality(
                channel_name="skin_temperature",
                sqi_score=0.0,
                is_usable=False,
                missing_sample_ratio=1.0,
                notes="UNAVAILABLE: Channel not provided in sample.",
            )

        sqi = timing_sqi
        usable = sqi >= self.config.min_channel_sqi_usable
        return ChannelQuality(
            channel_name="skin_temperature",
            sqi_score=round(sqi, 4),
            is_usable=usable,
            missing_sample_ratio=round(missing_ratio, 4),
            motion_artifact_detected=False,
            notes="ACCEPTABLE" if usable else "POOR_QUALITY: Timing discontinuity.",
        )

    # --- Window Sequence Helper ---

    def _assess_channel_window(
        self,
        channel_name: str,
        present_count: int,
        total_samples: int,
        total_expected_samples: int,
        motion_index: float,
        motion_detected: bool,
        timing_sqi: float,
        motion_susceptibility: float,
    ) -> ChannelQuality:
        """Evaluate channel quality over a temporal window."""
        # 1. Check if channel is entirely unavailable
        if present_count == 0:
            return ChannelQuality(
                channel_name=channel_name,
                sqi_score=0.0,
                is_usable=False,
                missing_sample_ratio=1.0,
                notes="UNAVAILABLE: Channel has no readings in window.",
            )

        # 2. Check if channel has insufficient sample history
        if present_count < self.config.min_history_samples:
            effective_missing_ratio = 1.0 - (present_count / max(total_samples, total_expected_samples))
            return ChannelQuality(
                channel_name=channel_name,
                sqi_score=round(max(0.1, (present_count / self.config.min_history_samples) * self.config.insufficient_history_penalty_cap), 4),
                is_usable=False,
                missing_sample_ratio=round(effective_missing_ratio, 4),
                motion_artifact_detected=motion_detected,
                notes=f"INSUFFICIENT_HISTORY: Only {present_count} samples (minimum required: {self.config.min_history_samples}).",
            )

        # 3. Channel is available with sufficient history
        effective_missing_ratio = max(0.0, min(1.0, 1.0 - (present_count / max(total_samples, total_expected_samples))))
        presence_ratio = present_count / total_samples

        # SQI balances presence ratio, timing quality, and motion corruption using configured weights
        motion_penalty = motion_index * motion_susceptibility
        base_score = (self.config.presence_weight * presence_ratio) + (self.config.timing_weight * timing_sqi)
        sqi = max(0.0, min(1.0, base_score - motion_penalty))
        usable = sqi >= self.config.min_channel_sqi_usable

        note = "ACCEPTABLE" if usable else "POOR_QUALITY: Degraded by missingness or motion."
        if motion_detected and motion_susceptibility > 0:
            note += " (Motion artifact detected)"

        return ChannelQuality(
            channel_name=channel_name,
            sqi_score=round(sqi, 4),
            is_usable=usable,
            missing_sample_ratio=round(effective_missing_ratio, 4),
            motion_artifact_detected=motion_detected if motion_susceptibility > 0 else False,
            notes=note,
        )

    # --- Aggregation Helper ---

    def _aggregate_quality(
        self,
        channels: Dict[str, ChannelQuality],
    ) -> tuple[float, bool]:
        """Aggregate active channel SQIs into overall SQI and determine data acceptability.
        
        Unavailable channels are omitted from the calculation rather than penalizing
        overall quality or receiving synthetic values.
        """
        # Active channels are those with non-zero availability in the telemetry
        active_channels = {
            name: q for name, q in channels.items()
            if "UNAVAILABLE" not in (q.notes or "")
        }

        # If no channels are provided at all
        if not active_channels:
            return 0.0, False

        # Primary physiological channels (at least one must be usable for downstream processing)
        primary_physiological = ["heart_rate", "rr_interval"]
        has_usable_primary = any(
            channels.get(p) and channels[p].is_usable
            for p in primary_physiological
        )

        # Weighted average across active channels
        total_weight = 0.0
        weighted_sqi_sum = 0.0

        for name, quality in active_channels.items():
            weight = self.config.channel_weights.get(name, 0.10)
            weighted_sqi_sum += quality.sqi_score * weight
            total_weight += weight

        if total_weight == 0.0:
            overall_sqi = sum(q.sqi_score for q in active_channels.values()) / len(active_channels)
        else:
            overall_sqi = weighted_sqi_sum / total_weight

        overall_sqi = round(max(0.0, min(1.0, overall_sqi)), 4)

        # Telemetry is acceptable if overall SQI passes threshold AND at least one primary signal is usable
        is_acceptable = (
            overall_sqi >= self.config.min_overall_sqi_acceptable
            and has_usable_primary
        )

        return overall_sqi, is_acceptable
