#!/usr/bin/env python3
"""AeroVital Core Engine — Minimal Development Smoke-Test Harness.

Exercises the real AeroVital Core Engine pipeline end-to-end against deterministic
synthetic telemetry and operational scenarios.

DISCLAIMER:
This harness is strictly a software development and verification smoke-test tool.
The AeroVital engine is an engineering prototype and is NOT clinically validated,
medically validated, or aviation-certified.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.intelligence.estimator import ProvisionalRuleBasedEstimator
from backend.core.intelligence.rules import ProvisionalEstimationOutput
from backend.core.pipeline import AeroVitalPipeline
from backend.core.preprocessing.windowing import WindowBuffer, WindowConfig
from backend.core.quality import AccelUnit, QualityConfig, SignalQualityAssessor
from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.context import MissionPhase, OperationalContext
from backend.core.schemas.result import FatigueEstimationResult
from backend.core.schemas.telemetry import TelemetrySample


class TrackingEstimator(ProvisionalRuleBasedEstimator):
    """Subclass of the approved ProvisionalRuleBasedEstimator that retains the last evaluation output for audit display."""

    def __init__(self, config=None):
        super().__init__(config=config)
        self.last_provisional: Optional[ProvisionalEstimationOutput] = None

    def evaluate(self, features, context=None, quality=None, baseline_version=None):
        provisional = super().evaluate(
            features=features,
            context=context,
            quality=quality,
            baseline_version=baseline_version,
        )
        self.last_provisional = provisional
        return provisional


# Reference deterministic timestamp for all test scenarios
BASE_TIME = datetime(2026, 9, 22, 10, 0, 0, tzinfo=timezone.utc)

_SENTINEL = object()


def make_sample(
    ts: datetime,
    hr: Any = _SENTINEL,
    rr: Any = _SENTINEL,
    accel: Any = _SENTINEL,
    spo2: Any = _SENTINEL,
    temp: Any = _SENTINEL,
) -> TelemetrySample:
    """Construct deterministic synthetic TelemetrySample."""
    hr_val = 70.0 if hr is _SENTINEL else hr
    # Default nominal RR gives RMSSD = 50.0ms (diffs = 50ms)
    rr_val = [800.0, 850.0, 800.0, 850.0, 800.0] if rr is _SENTINEL else rr
    accel_val = (0.0, 0.0, 1.0) if accel is _SENTINEL else accel
    spo2_val = 98.0 if spo2 is _SENTINEL else spo2
    temp_val = 36.5 if temp is _SENTINEL else temp

    ax, ay, az = accel_val if accel_val is not None else (None, None, None)
    return TelemetrySample(
        timestamp=ts,
        heart_rate=hr_val,
        rr_interval=rr_val,
        spo2=spo2_val,
        skin_temperature=temp_val,
        accel_x=ax,
        accel_y=ay,
        accel_z=az,
    )


def make_baseline(
    pilot_id: str = "PILOT-TEST-001",
    version: str = "BASELINE-2026-Q3-v1",
    resting_hr: float = 70.0,
    resting_rmssd: float = 50.0,
) -> PilotBaseline:
    """Construct deterministic calibrated PilotBaseline."""
    return PilotBaseline(
        pilot_id=pilot_id,
        baseline_version=version,
        created_at=datetime(2026, 9, 1, 8, 0, 0, tzinfo=timezone.utc),
        resting_heart_rate=resting_hr,
        baseline_rmssd=resting_rmssd,
        is_calibrated=True,
    )


def build_scenario_data(
    scenario: str,
) -> Tuple[PilotBaseline, Optional[OperationalContext], List[TelemetrySample], Optional[SignalQualityAssessor]]:
    """Build deterministic synthetic inputs matching the requirements of each scenario."""
    baseline = make_baseline(resting_hr=70.0, resting_rmssd=50.0)
    quality_assessor = None

    if scenario == "normal":
        # 1. NORMAL: Nominal HR, nominal RMSSD, benign cruise context
        context = OperationalContext(
            timestamp=BASE_TIME,
            external_g_load=1.0,
            mission_phase=MissionPhase.CRUISE,
        )
        samples = [
            make_sample(
                BASE_TIME + timedelta(seconds=i),
                hr=71.0,  # Delta +1 BPM <= 10.0 nominal max
                rr=[800.0, 850.0, 800.0, 850.0, 800.0],  # RMSSD 50.0ms, ratio 1.0 >= 0.85
            )
            for i in range(8)
        ]

    elif scenario == "workload":
        # 2. WORKLOAD: Elevated HR (+25 BPM), high G-load (3.5g), combat maneuver phase
        context = OperationalContext(
            timestamp=BASE_TIME,
            external_g_load=3.5,
            mission_phase=MissionPhase.COMBAT_MANEUVER,
        )
        samples = [
            make_sample(
                BASE_TIME + timedelta(seconds=i),
                hr=95.0,  # Delta +25 BPM > 10.0 workload threshold
                rr=[630.0, 635.0, 630.0, 635.0],
            )
            for i in range(8)
        ]

    elif scenario == "fatigue":
        # 3. FATIGUE: Nominal HR, depressed RMSSD (10ms, ratio 0.18 < 0.70), benign context
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=55.0)
        context = OperationalContext(
            timestamp=BASE_TIME,
            external_g_load=1.0,
            mission_phase=MissionPhase.CRUISE,
        )
        samples = [
            make_sample(
                BASE_TIME + timedelta(seconds=i),
                hr=71.0,
                rr=[850.0, 860.0, 850.0, 860.0, 850.0],  # Diffs 10ms -> RMSSD 10ms
            )
            for i in range(8)
        ]

    elif scenario == "missing-rr":
        # 4. MISSING-RR: Nominal HR available, but RR interval missing entirely
        context = OperationalContext(
            timestamp=BASE_TIME,
            external_g_load=1.0,
            mission_phase=MissionPhase.CRUISE,
        )
        samples = [
            make_sample(
                BASE_TIME + timedelta(seconds=i),
                hr=71.0,
                rr=None,  # Explicitly omitted
            )
            for i in range(8)
        ]

    elif scenario == "no-benign-context":
        # 5. NO-BENIGN-CONTEXT: Depressed RMSSD but operational context is completely unavailable
        baseline = make_baseline(resting_hr=70.0, resting_rmssd=55.0)
        context = None  # No operational context supplied
        samples = [
            make_sample(
                BASE_TIME + timedelta(seconds=i),
                hr=71.0,
                rr=[850.0, 860.0, 850.0, 860.0, 850.0],  # Low RMSSD pattern
            )
            for i in range(8)
        ]

    elif scenario == "poor-quality":
        # 6. POOR-QUALITY: Telemetry with severe dynamic acceleration (>1.2g)
        qa_cfg = QualityConfig(accel_unit=AccelUnit.G)
        quality_assessor = SignalQualityAssessor(config=qa_cfg)
        context = OperationalContext(
            timestamp=BASE_TIME,
            external_g_load=1.0,
            mission_phase=MissionPhase.CRUISE,
        )
        samples = [
            make_sample(
                BASE_TIME + timedelta(seconds=i),
                hr=72.0,
                accel=(3.5, -2.8, 4.0),  # Extreme dynamic motion
            )
            for i in range(8)
        ]

    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    return baseline, context, samples, quality_assessor


def run_scenario(scenario_name: str) -> None:
    """Execute the pipeline on the specified scenario and print the required report."""
    baseline, context, samples, quality_assessor = build_scenario_data(scenario_name)

    tracking_estimator = TrackingEstimator()
    pipeline = AeroVitalPipeline(
        baseline=baseline,
        quality_assessor=quality_assessor,
        estimator=tracking_estimator,
    )

    # Feed samples sequentially through the real pipeline
    results: List[FatigueEstimationResult] = pipeline.process_sequence(samples, context=context)

    latest_result = results[-1] if results else None
    provisional = tracking_estimator.last_provisional

    # Extract required fields according to Phase 5 specification
    final_state = latest_result.fatigue_state.value if latest_result else "None"
    candidate_state = provisional.candidate_state.value if provisional else "None"
    confidence = latest_result.confidence if latest_result else "None"
    overall_sqi = latest_result.overall_sqi if latest_result else "None"
    baseline_version = (
        latest_result.metadata.baseline_version_used if latest_result and latest_result.metadata else "None"
    )
    dominant_factors = latest_result.dominant_factors if latest_result else "None"
    evidence_trace = provisional.rule_evidence_trace if provisional else "None"
    timestamp = latest_result.timestamp.isoformat() if latest_result else "None"

    # Print exact compact report
    print(f"Scenario: {scenario_name}")
    print(f"Final state: {final_state}")
    print(f"Candidate state: {candidate_state}")
    print(f"Confidence: {confidence}")
    print(f"Overall SQI: {overall_sqi}")
    print(f"Baseline version: {baseline_version}")
    print(f"Dominant factors: {dominant_factors}")
    print(f"Evidence/rule trace: {evidence_trace}")
    print(f"Timestamp: {timestamp}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AeroVital Core Engine Smoke-Test Harness. "
                    "Feeds deterministic synthetic telemetry through the complete framework-independent pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Available Scenarios:
  normal             Nominal physiology concordant with baseline under benign cruise flight.
  workload           Elevated heart rate (+25 BPM) under combat maneuver (3.5g load).
  fatigue            Autonomic degradation (low RMSSD ratio) under confirmed benign cruise context.
  missing-rr         Omitted RR interval channel verifying that HRV is not fabricated.
  no-benign-context  Low RMSSD without benign context verifying that fatigue is not assumed.
  poor-quality       Severe dynamic motion corruption triggering quality abstention gating.
  all                Run all 6 scenarios in sequence.
""",
    )
    parser.add_argument(
        "--scenario",
        required=True,
        choices=["normal", "workload", "fatigue", "missing-rr", "no-benign-context", "poor-quality", "all"],
        help="The deterministic operational flight scenario to execute.",
    )

    args = parser.parse_args()

    scenarios = (
        ["normal", "workload", "fatigue", "missing-rr", "no-benign-context", "poor-quality"]
        if args.scenario == "all"
        else [args.scenario]
    )

    for i, sc in enumerate(scenarios):
        if i > 0:
            print("-" * 60)
        run_scenario(sc)


if __name__ == "__main__":
    main()
