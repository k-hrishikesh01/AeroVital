#!/usr/bin/env python3
"""AeroVital Intelligence Engine Execution on Synthetic Dataset v1.

Executes the framework-independent AeroVital Core Intelligence Engine (`backend.core.pipeline.pipeline.AeroVitalPipeline`)
against all 60 generated sessions across all 5 scenarios without altering algorithm parameters or thresholds.

Captures:
- Input signal quality (overall SQI and channel usability).
- Extracted features (descriptive HR/HRV and baseline deviation ratios).
- Discrete operational fatigue classification (`NORMAL`, `ELEVATED_WORKLOAD`, `FATIGUE`, `INSUFFICIENT_DATA`).
- Independent confidence evaluation and abstention gating.
- Contributing dominant factors and rule evidence traces.
- Session-level and scenario-level classification distributions.

Outputs:
- engine_execution_results.json
- engine_execution_report.md
"""

import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

DATASET_DIR = Path(__file__).resolve().parent
REPO_ROOT = DATASET_DIR.parent.parent.parent

# Add repository root so backend.core is importable
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.pipeline.pipeline import AeroVitalPipeline
from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.context import MissionPhase, OperationalContext
from backend.core.schemas.telemetry import TelemetrySample


def run_evaluation():
    print("===============================================================")
    print(" AeroVital Core Intelligence Engine Execution on Synthetic v1")
    print(" Target: 60 Sessions across 5 Scenarios (216,000 observations)")
    print("===============================================================\n")

    with open(DATASET_DIR / "participants.json", "r", encoding="utf-8") as f:
        participants = {p["pilot_id"]: p for p in json.load(f)}

    with open(DATASET_DIR / "sessions.json", "r", encoding="utf-8") as f:
        sessions_meta = json.load(f)

    # Read records grouped by session
    print("Step 1: Ingesting dataset records by session...")
    records_by_session: Dict[str, List[Dict[str, Any]]] = {}
    with open(DATASET_DIR / "synthetic_physiological_dataset.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            s_id = rec["session_id"]
            if s_id not in records_by_session:
                records_by_session[s_id] = []
            records_by_session[s_id].append(rec)

    print(f" -> Loaded records for {len(records_by_session)} sessions.\n")

    # Step 2: Execute engine session by session
    print("Step 2: Executing AeroVitalPipeline across all sessions...")
    scenario_results: Dict[str, Any] = {
        "NORMAL_BASELINE": {"total_windows": 0, "state_counts": Counter(), "confidences": [], "sqis": [], "factors": Counter()},
        "ELEVATED_COGNITIVE_WORKLOAD": {"total_windows": 0, "state_counts": Counter(), "confidences": [], "sqis": [], "factors": Counter()},
        "FATIGUE_PHYSIOLOGICAL": {"total_windows": 0, "state_counts": Counter(), "confidences": [], "sqis": [], "factors": Counter()},
        "DEGRADED_SIGNAL_QUALITY": {"total_windows": 0, "state_counts": Counter(), "confidences": [], "sqis": [], "factors": Counter()},
        "MIXED_OPERATIONAL_CONDITIONS": {"total_windows": 0, "state_counts": Counter(), "confidences": [], "sqis": [], "factors": Counter()},
    }

    session_summaries: List[Dict[str, Any]] = []
    representative_examples: Dict[str, Any] = {}

    start_time_all = time.time()

    for s_meta in sessions_meta:
        s_id = s_meta["session_id"]
        p_id = s_meta["participant_id"]
        scenario = s_meta["scenario"]
        recs = records_by_session[s_id]

        p = participants[p_id]
        baseline = PilotBaseline(
            pilot_id=p["pilot_id"],
            baseline_version=p["baseline_version"],
            resting_heart_rate=p["resting_heart_rate"],
            baseline_rmssd=p["baseline_rmssd"],
            baseline_sdnn=p["baseline_sdnn"],
            baseline_mean_rr=p["baseline_mean_rr"],
            created_at=datetime.fromisoformat(p["calibration_timestamp"]),
        )

        pipeline = AeroVitalPipeline(baseline=baseline)

        session_windows = 0
        session_states = Counter()
        session_confidences = []
        session_sqis = []

        # Process sequential stream of 3600 samples
        for r in recs:
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
                mission_phase=MissionPhase(r["mission_phase"]) if r["mission_phase"] else None,
                external_g_load=r["external_g_load"],
                flight_duration_sec=r["flight_duration_sec"],
            )

            res = pipeline.process_sample(s, context=ctx)
            if res is not None:
                session_windows += 1
                state_str = res.fatigue_state.value
                session_states[state_str] += 1
                session_confidences.append(res.confidence)
                session_sqis.append(res.overall_sqi)

                scenario_results[scenario]["total_windows"] += 1
                scenario_results[scenario]["state_counts"][state_str] += 1
                scenario_results[scenario]["confidences"].append(res.confidence)
                scenario_results[scenario]["sqis"].append(res.overall_sqi)
                for f_str in res.dominant_factors:
                    scenario_results[scenario]["factors"][f_str] += 1

                # Capture representative examples
                if state_str not in representative_examples:
                    representative_examples[state_str] = {
                        "session_id": s_id,
                        "scenario": scenario,
                        "timestamp": res.timestamp.isoformat(),
                        "fatigue_state": state_str,
                        "confidence": round(res.confidence, 3),
                        "overall_sqi": round(res.overall_sqi, 3),
                        "dominant_factors": res.dominant_factors,
                        "baseline_version": res.metadata.baseline_version_used,
                        "estimator_id": res.metadata.estimator_id,
                    }

        summary_entry = {
            "session_id": s_id,
            "participant_id": p_id,
            "scenario": scenario,
            "evaluated_windows": session_windows,
            "state_breakdown": dict(session_states),
            "mean_confidence": round(float(np.mean(session_confidences)), 3) if session_confidences else 0.0,
            "mean_sqi": round(float(np.mean(session_sqis)), 3) if session_sqis else 0.0,
        }
        session_summaries.append(summary_entry)
        print(f"  [{s_id}] {p_id} | {scenario:<28} | Windows: {session_windows} | States: {dict(session_states)} | Conf: {summary_entry['mean_confidence']} | SQI: {summary_entry['mean_sqi']}")

    total_time = time.time() - start_time_all
    print(f"\n -> Finished evaluating all 60 sessions in {total_time:.2f}s ({total_time / 60.0:.2f} min).\n")

    # Step 3: Serialize results to JSON
    scenario_export: Dict[str, Any] = {}
    for sc, data in scenario_results.items():
        total_w = data["total_windows"]
        scenario_export[sc] = {
            "total_windows_evaluated": total_w,
            "classification_counts": dict(data["state_counts"]),
            "classification_percentages": {k: round(100.0 * v / total_w, 2) for k, v in data["state_counts"].items()},
            "mean_confidence": round(float(np.mean(data["confidences"])), 3) if data["confidences"] else 0.0,
            "mean_sqi": round(float(np.mean(data["sqis"])), 3) if data["sqis"] else 0.0,
            "top_dominant_factors": [{"factor": f, "count": c} for f, c in data["factors"].most_common(5)],
        }

    output_payload = {
        "execution_metadata": {
            "engine_orchestrator": "AeroVitalPipeline",
            "engine_version": "1.0.0",
            "evaluator": "ProvisionalRuleBasedEstimator",
            "confidence_evaluator": "ConfidenceEvaluator",
            "dataset_id": "aerovital-synthetic-v1",
            "total_sessions_evaluated": len(sessions_meta),
            "total_samples_processed": 216000,
            "total_windows_evaluated": sum(d["total_windows"] for d in scenario_results.values()),
            "execution_duration_sec": round(total_time, 2),
            "execution_timestamp": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "Provisional prototype intelligence engine evaluation for testing only; not clinically or operationally validated.",
        },
        "scenario_evaluations": scenario_export,
        "representative_examples": representative_examples,
        "session_summaries": session_summaries,
    }

    results_json_path = DATASET_DIR / "engine_execution_results.json"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)
    print(f" -> Saved Engine Execution Results to: {results_json_path.name}")

    # Step 4: Write Engine Execution Report Markdown
    report_md_path = DATASET_DIR / "engine_execution_report.md"
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("# AeroVital Core Intelligence Engine Execution Report\n\n")
        f.write(f"**Execution Timestamp:** `{output_payload['execution_metadata']['execution_timestamp']}`  \n")
        f.write(f"**Engine Orchestrator:** `{output_payload['execution_metadata']['engine_orchestrator']}` (v1.0.0)  \n")
        f.write(f"**Dataset Evaluated:** `{output_payload['execution_metadata']['dataset_id']}` ({len(sessions_meta)} sessions, 216,000 observations)  \n")
        f.write(f"**Total Windows Evaluated:** {output_payload['execution_metadata']['total_windows_evaluated']:,}  \n")
        f.write(f"**Execution Throughput:** {216000.0 / total_time:.1f} samples/sec ({total_time:.2f}s total run time)  \n\n")

        f.write("> [!NOTE]\n")
        f.write("> **Provisional Research Disclaimer:** Synthetic scenario labels represent experimental configurations, "
                "not clinical ground truth. The AeroVital Core Intelligence Engine operates with strict non-imputation "
                "and rule-based structural evidence evaluation. These results demonstrate deterministic pipeline behavior, "
                "not clinical diagnostic accuracy or operational pilot safety certification.\n\n")

        f.write("## Scenario Evaluation Breakdown\n\n")
        f.write("| Scenario | Windows | NORMAL (%) | ELEVATED_WORKLOAD (%) | FATIGUE (%) | INSUFFICIENT_DATA (%) | Mean Conf | Mean SQI |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")

        for sc, sc_data in scenario_export.items():
            pcts = sc_data["classification_percentages"]
            f.write(f"| **{sc}** | {sc_data['total_windows_evaluated']:,} | "
                    f"{pcts.get('NORMAL', 0.0)}% | "
                    f"{pcts.get('ELEVATED_WORKLOAD', 0.0)}% | "
                    f"{pcts.get('FATIGUE', 0.0)}% | "
                    f"{pcts.get('INSUFFICIENT_DATA', 0.0)}% | "
                    f"{sc_data['mean_confidence']} | "
                    f"{sc_data['mean_sqi']} |\n")

        f.write("\n\n## Representative Engine Outputs by State\n\n")
        for state_name, ex in representative_examples.items():
            f.write(f"### State: `{state_name}`\n")
            f.write(f"- **Triggering Scenario:** `{ex['scenario']}` (Session `{ex['session_id']}`)\n")
            f.write(f"- **Confidence:** `{ex['confidence']}` | **Overall SQI:** `{ex['overall_sqi']}`\n")
            f.write(f"- **Baseline Version Used:** `{ex['baseline_version']}`\n")
            f.write(f"- **Dominant Rationale Factors:**\n")
            for factor in ex["dominant_factors"]:
                f.write(f"  - *{factor}*\n")
            f.write("\n")

        f.write("## Top Dominant Contributing Factors Across Scenarios\n\n")
        for sc, sc_data in scenario_export.items():
            f.write(f"### {sc}\n")
            for tf in sc_data["top_dominant_factors"]:
                f.write(f"- **{tf['factor']}** ({tf['count']:,} windows)\n")
            f.write("\n")

    print(f" -> Saved Engine Execution Report to: {report_md_path.name}")
    print("\n[SUCCESS] Engine Evaluation Complete!")


if __name__ == "__main__":
    run_evaluation()
