"""Top-Level Core Pipeline Orchestrator for AeroVital.

Implements AeroVitalPipeline: a framework-independent, sensor-agnostic coordinator
that connects the approved core pipeline stages:
Telemetry
  → Validation (Step 2)
  → Signal Quality (Step 3)
  → Preprocessing / Windowing (Step 4)
  → Feature Extraction (Step 5)
  → Pilot Baseline Normalization (Step 6)
  → State Estimation (Step 7)
  → Confidence & Final Result (Step 8)

STRICT PRINCIPLES:
1. Orchestration only: zero physiological thresholds, zero fatigue equations, zero confidence formulas.
2. Framework-independent: no Django, no FastAPI, no network, no database access.
3. No data fabrication: missing channels remain None, insufficient history returns None, invalid telemetry raises.
4. Deterministic & pure: identical inputs and configuration yield identical outputs.
5. Preserves all provenances, disclaimers, and metadata through the final FatigueEstimationResult.
"""

from datetime import datetime
from typing import List, Optional, Sequence

from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.context import OperationalContext
from backend.core.schemas.features import FeatureVector
from backend.core.schemas.quality import QualityAssessment
from backend.core.schemas.result import FatigueEstimationResult
from backend.core.schemas.telemetry import TelemetrySample

from backend.core.validation.validator import TelemetryValidator
from backend.core.quality.assessment import SignalQualityAssessor
from backend.core.preprocessing.windowing import WindowBuffer, WindowSnapshot
from backend.core.features.extractor import FeatureExtractor
from backend.core.baseline.normalizer import BaselineNormalizer
from backend.core.intelligence.estimator import ProvisionalRuleBasedEstimator
from backend.core.confidence.evaluator import ConfidenceEvaluator


class AeroVitalPipeline:
    """End-to-end orchestrator for the AeroVital Core Intelligence Engine."""

    def __init__(
        self,
        baseline: Optional[PilotBaseline] = None,
        validator: Optional[TelemetryValidator] = None,
        quality_assessor: Optional[SignalQualityAssessor] = None,
        window_buffer: Optional[WindowBuffer] = None,
        feature_extractor: Optional[FeatureExtractor] = None,
        baseline_normalizer: Optional[BaselineNormalizer] = None,
        estimator: Optional[ProvisionalRuleBasedEstimator] = None,
        confidence_evaluator: Optional[ConfidenceEvaluator] = None,
    ):
        """Initialize the pipeline with dependency-injected components.
        
        Args:
            baseline: Optional pilot-specific calibrated baseline profile.
            validator: Telemetry and context validator (Step 2).
            quality_assessor: Multi-channel signal quality evaluator (Step 3).
            window_buffer: Rolling temporal window buffer (Step 4).
            feature_extractor: Window feature extraction engine (Step 5).
            baseline_normalizer: Pilot baseline comparison normalizer (Step 6).
            estimator: Provisional state rule evaluator (Step 7).
            confidence_evaluator: Confidence evaluator and final result generator (Step 8).
        """
        self.baseline = baseline
        self.validator = validator or TelemetryValidator()
        self.quality_assessor = quality_assessor or SignalQualityAssessor()
        self.window_buffer = window_buffer or WindowBuffer()
        self.feature_extractor = feature_extractor or FeatureExtractor()
        self.baseline_normalizer = baseline_normalizer or BaselineNormalizer()
        self.estimator = estimator or ProvisionalRuleBasedEstimator()
        self.confidence_evaluator = confidence_evaluator or ConfidenceEvaluator()

        self._last_sample_timestamp: Optional[datetime] = None
        self._last_context_timestamp: Optional[datetime] = None

    def set_baseline(self, baseline: Optional[PilotBaseline]) -> None:
        """Update or clear the active pilot-specific baseline profile."""
        self.baseline = baseline

    def get_baseline(self) -> Optional[PilotBaseline]:
        """Retrieve the currently configured pilot baseline, if any."""
        return self.baseline

    def reset(self) -> None:
        """Reset internal buffer state and timestamp tracking."""
        self.window_buffer = WindowBuffer(config=self.window_buffer.config)
        self._last_sample_timestamp = None
        self._last_context_timestamp = None

    def process_sample(
        self,
        sample: TelemetrySample,
        context: Optional[OperationalContext] = None,
    ) -> Optional[FatigueEstimationResult]:
        """Process a single streaming telemetry sample through the pipeline.
        
        Args:
            sample: Incoming TelemetrySample from sensor or wearable adapter.
            context: Optional operational flight context (G-load, phase, duration).
            
        Returns:
            FatigueEstimationResult if the window buffer contains sufficient history,
            or None if the buffer is still accumulating required observations.
            
        Raises:
            SignalValidationError: If telemetry sample or context violates sanity bounds.
        """
        # 1. Validate incoming telemetry sample
        validated_sample = self.validator.validate_sample(
            sample=sample,
            previous_timestamp=self._last_sample_timestamp,
        )
        self._last_sample_timestamp = validated_sample.timestamp

        # 2. Validate operational context if supplied
        validated_context = None
        if context is not None:
            # If context timestamp is advancing or retrograding relative to previous, check ordering
            prev_ctx_ts = None
            if self._last_context_timestamp is not None and context.timestamp != self._last_context_timestamp:
                prev_ctx_ts = self._last_context_timestamp

            validated_context = self.validator.validate_context(
                context=context,
                previous_timestamp=prev_ctx_ts,
            )
            self._last_context_timestamp = validated_context.timestamp

        # 3. Add to temporal rolling buffer
        self.window_buffer.add_sample(validated_sample)

        # 4. Check window sufficiency: if insufficient history, do not fabricate results
        if not self.window_buffer.is_ready():
            return None

        snapshot = self.window_buffer.snapshot()
        if snapshot is None:
            return None

        # 5. Evaluate window through downstream stages
        return self._evaluate_window(snapshot=snapshot, context=validated_context)

    def process_sequence(
        self,
        samples: Sequence[TelemetrySample],
        context: Optional[OperationalContext] = None,
    ) -> List[FatigueEstimationResult]:
        """Process a chronological sequence of samples, returning all emitted window results.
        
        Args:
            samples: Ordered sequence of TelemetrySamples.
            context: Optional operational flight context.
            
        Returns:
            List of FatigueEstimationResults emitted as windows become ready.
        """
        results: List[FatigueEstimationResult] = []
        for sample in samples:
            res = self.process_sample(sample, context=context)
            if res is not None:
                results.append(res)
        return results

    def process_window_samples(
        self,
        samples: Sequence[TelemetrySample],
        context: Optional[OperationalContext] = None,
    ) -> FatigueEstimationResult:
        """Process an explicit batch of window samples directly without maintaining buffer state.
        
        Args:
            samples: Ordered sequence of TelemetrySamples constituting an entire window.
            context: Optional operational flight context.
            
        Returns:
            Definitive FatigueEstimationResult for the given window samples.
            
        Raises:
            ValueError: If fewer samples than min_samples_required are provided.
            SignalValidationError: If any sample or context fails input validation.
        """
        min_required = self.window_buffer.config.min_samples_required
        if len(samples) < min_required:
            raise ValueError(
                f"Insufficient sample history for window evaluation: "
                f"got {len(samples)} samples, required minimum {min_required}."
            )

        # Validate all samples in sequence
        prev_ts: Optional[datetime] = None
        validated_samples: List[TelemetrySample] = []
        for s in samples:
            v_sample = self.validator.validate_sample(s, previous_timestamp=prev_ts)
            validated_samples.append(v_sample)
            prev_ts = v_sample.timestamp

        # Validate context if provided
        validated_context = None
        if context is not None:
            validated_context = self.validator.validate_context(context)

        # Create window snapshot
        snapshot = WindowSnapshot(
            window_start=validated_samples[0].timestamp,
            window_end=validated_samples[-1].timestamp,
            samples=validated_samples,
        )

        return self._evaluate_window(snapshot=snapshot, context=validated_context)

    def _evaluate_window(
        self,
        snapshot: WindowSnapshot,
        context: Optional[OperationalContext] = None,
    ) -> FatigueEstimationResult:
        """Coordinate execution of Stages 3 through 8 over an evaluated window snapshot.
        
        This private helper strictly orchestrates: it does not contain or evaluate
        any physiological rules, threshold constants, or confidence formulas.
        """
        # Stage 3: Signal Quality Assessment over the window
        quality = self.quality_assessor.assess_window(snapshot.samples)

        # Stage 5: Descriptive Feature Extraction
        raw_features = self.feature_extractor.extract_features(snapshot)

        # Stage 6: Pilot Baseline Normalization
        normalized_features = self.baseline_normalizer.normalize(
            features=raw_features,
            baseline=self.baseline,
        )

        # Stage 7: Intelligence / State Estimation
        baseline_version = self.baseline.baseline_version if self.baseline is not None else None
        provisional = self.estimator.evaluate(
            features=normalized_features,
            context=context,
            quality=quality,
            baseline_version=baseline_version,
        )

        # Stage 8: Confidence Evaluation & Final Result Generation
        result = self.confidence_evaluator.evaluate(
            provisional=provisional,
            quality=quality,
            features=normalized_features,
            context=context,
        )

        return result
