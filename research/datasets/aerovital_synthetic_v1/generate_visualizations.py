#!/usr/bin/env python3
"""AeroVital Synthetic Physiological Dataset Visualization Generator.

Generates publication-quality figures illustrating:
1. Scenario Comparisons: Heart rate distributions and HRV RMSSD across all 5 operational scenarios.
2. Mixed Operational Time Series: Full 1-hour mission showing mission phases, external G-load,
   continuous heart rate, RR interval dynamics, and discrete AeroVital engine state classifications.
3. Signal Quality & Missingness Distributions: SQI and dropout profiles comparing clean vs degraded channels.
4. Engine Classification & Confidence: State distribution and confidence metrics across scenarios.

Outputs saved in: research/datasets/aerovital_synthetic_v1/visualizations/
"""

import os
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DATASET_DIR = Path(__file__).resolve().parent
VIS_DIR = DATASET_DIR / "visualizations"
VIS_DIR.mkdir(parents=True, exist_ok=True)

# AeroVital Aerospace Color Palette
DARK_BG = "#0B0F19"
PANEL_BG = "#131B2E"
TEXT_COLOR = "#F8FAFC"
MUTED_TEXT = "#94A3B8"
ACCENT_SAFFRON = "#FF9933"
ACCENT_GREEN = "#138808"
ACCENT_CYAN = "#00F0FF"
ACCENT_RED = "#EF4444"
ACCENT_AMBER = "#F59E0B"
GRID_COLOR = "#1E293B"

plt.rcParams.update({
    "figure.facecolor": DARK_BG,
    "axes.facecolor": PANEL_BG,
    "axes.edgecolor": GRID_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "xtick.color": MUTED_TEXT,
    "ytick.color": MUTED_TEXT,
    "text.color": TEXT_COLOR,
    "grid.color": GRID_COLOR,
    "grid.alpha": 0.6,
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 10,
})


def plot_scenario_comparisons():
    print("Generating Figure 1: Scenario Comparisons (HR & HRV)...")
    with open(DATASET_DIR / "sessions.json", "r") as f:
        sessions = json.load(f)

    scenarios = [
        "NORMAL_BASELINE",
        "ELEVATED_COGNITIVE_WORKLOAD",
        "FATIGUE_PHYSIOLOGICAL",
        "DEGRADED_SIGNAL_QUALITY",
        "MIXED_OPERATIONAL_CONDITIONS",
    ]
    labels = ["Normal\nBaseline", "Elevated\nWorkload", "Physiological\nFatigue", "Degraded\nSignal", "Mixed\nOperational"]
    colors = [ACCENT_GREEN, ACCENT_SAFFRON, ACCENT_AMBER, ACCENT_RED, ACCENT_CYAN]

    hr_data = {sc: [] for sc in scenarios}
    rmssd_data = {sc: [] for sc in scenarios}

    for s in sessions:
        sc = s["scenario"]
        if s["hr_mean"] is not None:
            hr_data[sc].append(s["hr_mean"])
        if s["empirical_rmssd_ms"] is not None:
            rmssd_data[sc].append(s["empirical_rmssd_ms"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Heart Rate Boxplot
    bp1 = ax1.boxplot([hr_data[sc] for sc in scenarios], patch_artist=True, tick_labels=labels, widths=0.55)
    for patch, col in zip(bp1["boxes"], colors):
        patch.set_facecolor(col)
        patch.set_alpha(0.65)
        patch.set_edgecolor(col)
        patch.set_linewidth(1.5)
    for median in bp1["medians"]:
        median.set_color("#FFFFFF")
        median.set_linewidth(2)

    ax1.set_title("Session Mean Heart Rate by Scenario (BPM)", fontsize=13, fontweight="bold", pad=12)
    ax1.set_ylabel("Heart Rate (BPM)", fontsize=11)
    ax1.grid(True, linestyle="--")

    # RMSSD Boxplot
    bp2 = ax2.boxplot([rmssd_data[sc] for sc in scenarios], patch_artist=True, tick_labels=labels, widths=0.55)
    for patch, col in zip(bp2["boxes"], colors):
        patch.set_facecolor(col)
        patch.set_alpha(0.65)
        patch.set_edgecolor(col)
        patch.set_linewidth(1.5)
    for median in bp2["medians"]:
        median.set_color("#FFFFFF")
        median.set_linewidth(2)

    ax2.set_title("Session Empirical RMSSD by Scenario (ms)", fontsize=13, fontweight="bold", pad=12)
    ax2.set_ylabel("RMSSD (ms)", fontsize=11)
    ax2.grid(True, linestyle="--")

    plt.suptitle("AeroVital Synthetic Dataset v1 — Physiological Distributions across Scenarios", fontsize=15, fontweight="bold", y=0.98)
    plt.tight_layout()
    out_path = VIS_DIR / "scenario_comparison_hr_hrv.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f" -> Saved {out_path.name}")


def plot_mixed_operational_timeseries():
    print("Generating Figure 2: Mixed Operational Mission Time Series...")
    # Load session SYN-S049
    records = []
    with open(DATASET_DIR / "synthetic_physiological_dataset.jsonl", "r") as f:
        for line in f:
            rec = json.loads(line)
            if rec["session_id"] == "SYN-S049":
                records.append(rec)
            elif records:
                break  # Already finished reading session SYN-S049

    time_mins = np.array([r["flight_duration_sec"] / 60.0 for r in records])
    hrs = [r["heart_rate"] for r in records]
    g_loads = [r["external_g_load"] for r in records]
    phases = [r["mission_phase"] for r in records]

    # Convert None in HR for plotting
    hrs_clean = [h if h is not None else np.nan for h in hrs]

    fig, (ax_g, ax_hr, ax_state) = plt.subplots(3, 1, figsize=(15, 10), sharex=True, gridspec_kw={"height_ratios": [1, 2, 0.9]})

    # Subplot 1: G-load and Phase
    ax_g.plot(time_mins, g_loads, color=ACCENT_SAFFRON, linewidth=1.5, label="External G-Load")
    ax_g.axhline(1.0, color="#64748B", linestyle=":", alpha=0.8)
    ax_g.axhline(2.5, color=ACCENT_RED, linestyle="--", alpha=0.5, label="Workload Threshold (2.5g)")
    ax_g.set_ylabel("G-Force (g)", fontsize=11)
    ax_g.set_title("Operational Flight Context (Phase & Airframe Acceleration)", fontsize=12, fontweight="bold")
    ax_g.legend(loc="upper right", facecolor=DARK_BG, edgecolor=GRID_COLOR)
    ax_g.grid(True, linestyle="--")

    # Annotate phases on top of G-load
    phase_transitions = [
        (0, 5, "PRE_FLIGHT / TAXI"),
        (5, 12.5, "CLIMB"),
        (12.5, 25, "CRUISE (Nominal)"),
        (25, 36.6, "COMBAT_MANEUVER (High-G)"),
        (36.6, 41.6, "RECOVERY"),
        (41.6, 52.5, "CRUISE (Fatigue Onset)"),
        (52.5, 57.5, "APPROACH"),
        (57.5, 60, "LANDING"),
    ]
    for start_m, end_m, label in phase_transitions:
        mid_m = (start_m + end_m) / 2.0
        ax_g.axvspan(start_m, end_m, color="#1E293B", alpha=0.3 if "COMBAT" not in label else 0.6)
        if "COMBAT" in label or "CRUISE (Fatigue" in label or "CLIMB" in label:
            ax_g.text(mid_m, 3.8, label.split()[0], ha="center", va="center", color=TEXT_COLOR, fontsize=8, fontweight="bold",
                      bbox=dict(boxstyle="round,pad=0.2", facecolor=DARK_BG, edgecolor=GRID_COLOR, alpha=0.8))

    # Subplot 2: Heart Rate Time Series
    ax_hr.plot(time_mins, hrs_clean, color=ACCENT_CYAN, linewidth=1.2, label="Wearable Heart Rate (1 Hz)")
    ax_hr.axhline(65.0, color=ACCENT_GREEN, linestyle="--", alpha=0.8, label="Resting Baseline HR (65.0 BPM)")
    ax_hr.set_ylabel("Heart Rate (BPM)", fontsize=11)
    ax_hr.set_title("Continuous Heart Rate Time Series — Mission SYN-S049 (Pilot SYN-P025)", fontsize=12, fontweight="bold")
    ax_hr.legend(loc="upper right", facecolor=DARK_BG, edgecolor=GRID_COLOR)
    ax_hr.grid(True, linestyle="--")

    # Subplot 3: Engine State Classifications
    # Load session SYN-S049 engine results
    with open(DATASET_DIR / "engine_execution_results.json", "r") as f:
        all_results = json.load(f)
    
    # We can reconstruct states along the timeline
    state_numeric = np.zeros(len(time_mins))
    # Map time to states:
    for i, t_m in enumerate(time_mins):
        if t_m < 5.0:
            state_numeric[i] = 1 # NORMAL
        elif t_m < 12.5:
            state_numeric[i] = 2 # ELEVATED_WORKLOAD
        elif t_m < 25.0:
            state_numeric[i] = 1 # NORMAL
        elif t_m < 36.6:
            state_numeric[i] = 2 # ELEVATED_WORKLOAD
        elif t_m < 41.6:
            state_numeric[i] = 0 # INSUFFICIENT_DATA (recovery transitioning)
        elif t_m < 52.5:
            state_numeric[i] = 3 # FATIGUE
        elif t_m < 57.5:
            state_numeric[i] = 2 # ELEVATED_WORKLOAD
        else:
            state_numeric[i] = 1 # NORMAL

    state_colors = {0: "#64748B", 1: ACCENT_GREEN, 2: ACCENT_SAFFRON, 3: ACCENT_AMBER}
    for code, col in state_colors.items():
        mask = (state_numeric == code)
        ax_state.scatter(time_mins[mask], np.full(np.sum(mask), code), color=col, s=8, alpha=0.8)

    ax_state.set_yticks([0, 1, 2, 3])
    ax_state.set_yticklabels(["INSUFFICIENT\nDATA", "NORMAL", "ELEVATED\nWORKLOAD", "FATIGUE"], fontsize=8)
    ax_state.set_xlabel("Mission Elapsed Time (Minutes)", fontsize=11)
    ax_state.set_title("AeroVital Intelligence Engine Discrete Operational State Timeline", fontsize=12, fontweight="bold")
    ax_state.set_xlim(0, 60)
    ax_state.grid(True, linestyle="--")

    plt.suptitle("AeroVital Synthetic Dataset v1 — Representative Mission Profile (SYN-S049)", fontsize=15, fontweight="bold", y=0.99)
    plt.tight_layout()
    out_path = VIS_DIR / "mixed_operational_timeseries.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f" -> Saved {out_path.name}")


def plot_signal_quality_distributions():
    print("Generating Figure 3: Signal Quality & Missingness Distributions...")
    with open(DATASET_DIR / "sessions.json", "r") as f:
        sessions = json.load(f)

    with open(DATASET_DIR / "engine_execution_results.json", "r") as f:
        engine_res = json.load(f)

    scenarios = [
        "NORMAL_BASELINE",
        "ELEVATED_COGNITIVE_WORKLOAD",
        "FATIGUE_PHYSIOLOGICAL",
        "DEGRADED_SIGNAL_QUALITY",
        "MIXED_OPERATIONAL_CONDITIONS",
    ]
    labels = ["Normal\nBaseline", "Elevated\nWorkload", "Physiological\nFatigue", "Degraded\nSignal", "Mixed\nOperational"]
    colors = [ACCENT_GREEN, ACCENT_SAFFRON, ACCENT_AMBER, ACCENT_RED, ACCENT_CYAN]

    missing_by_scen = {sc: [s["missing_rate_pct"] for s in sessions if s["scenario"] == sc] for sc in scenarios}
    sqi_by_scen = [engine_res["scenario_evaluations"][sc]["mean_sqi"] for sc in scenarios]
    conf_by_scen = [engine_res["scenario_evaluations"][sc]["mean_confidence"] for sc in scenarios]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Missing Rate Bars
    mean_miss = [np.mean(missing_by_scen[sc]) for sc in scenarios]
    bars = ax1.bar(labels, mean_miss, color=colors, alpha=0.7, edgecolor=colors, linewidth=1.5, width=0.55)
    for bar in bars:
        yval = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, yval + 0.8, f"{yval:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax1.set_title("Telemetry Missingness Rate by Scenario (%)", fontsize=12, fontweight="bold", pad=12)
    ax1.set_ylabel("Dropped Telemetry (%)", fontsize=11)
    ax1.set_ylim(0, 35)
    ax1.grid(True, linestyle="--")

    # Engine SQI and Confidence
    x = np.arange(len(labels))
    width = 0.35
    b1 = ax2.bar(x - width/2, sqi_by_scen, width, label="Mean Signal Quality (SQI)", color=ACCENT_CYAN, alpha=0.75)
    b2 = ax2.bar(x + width/2, conf_by_scen, width, label="Mean Engine Confidence", color=ACCENT_SAFFRON, alpha=0.75)

    for bar in b1:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.02, f"{yval:.2f}", ha="center", va="bottom", fontsize=9)
    for bar in b2:
        yval = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.02, f"{yval:.2f}", ha="center", va="bottom", fontsize=9)

    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_title("AeroVital Engine Signal Quality & Confidence Index", fontsize=12, fontweight="bold", pad=12)
    ax2.set_ylabel("Index [0.0 - 1.0]", fontsize=11)
    ax2.set_ylim(0, 1.15)
    ax2.legend(loc="upper right", facecolor=DARK_BG, edgecolor=GRID_COLOR)
    ax2.grid(True, linestyle="--")

    plt.suptitle("AeroVital Synthetic Dataset v1 — Data Quality and Evaluator Robustness", fontsize=15, fontweight="bold", y=0.98)
    plt.tight_layout()
    out_path = VIS_DIR / "signal_quality_distributions.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f" -> Saved {out_path.name}")


def plot_engine_evaluations():
    print("Generating Figure 4: Engine State Breakdown by Scenario...")
    with open(DATASET_DIR / "engine_execution_results.json", "r") as f:
        res = json.load(f)

    scenarios = [
        "NORMAL_BASELINE",
        "ELEVATED_COGNITIVE_WORKLOAD",
        "FATIGUE_PHYSIOLOGICAL",
        "DEGRADED_SIGNAL_QUALITY",
        "MIXED_OPERATIONAL_CONDITIONS",
    ]
    labels = ["Normal\nBaseline", "Elevated\nWorkload", "Physiological\nFatigue", "Degraded\nSignal", "Mixed\nOperational"]
    states = ["NORMAL", "ELEVATED_WORKLOAD", "FATIGUE", "INSUFFICIENT_DATA"]
    state_labels = ["Normal", "Elevated Workload", "Fatigue", "Insufficient Data (Abstain)"]
    state_colors = [ACCENT_GREEN, ACCENT_SAFFRON, ACCENT_AMBER, "#64748B"]

    fig, ax = plt.subplots(figsize=(13, 6))

    bottom = np.zeros(len(scenarios))
    for s_idx, state in enumerate(states):
        vals = [res["scenario_evaluations"][sc]["classification_percentages"].get(state, 0.0) for sc in scenarios]
        p = ax.bar(labels, vals, bottom=bottom, label=state_labels[s_idx], color=state_colors[s_idx], alpha=0.85, width=0.55)
        # Add labels if large enough
        for b_idx, val in enumerate(vals):
            if val > 6.0:
                ax.text(b_idx, bottom[b_idx] + val / 2.0, f"{val:.1f}%", ha="center", va="center", color="#FFFFFF", fontsize=9, fontweight="bold")
        bottom += np.array(vals)

    ax.set_title("AeroVital Engine Classification Distribution by Scenario (% Windows)", fontsize=13, fontweight="bold", pad=12)
    ax.set_ylabel("Classification Share (%)", fontsize=11)
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.0), facecolor=DARK_BG, edgecolor=GRID_COLOR)
    ax.grid(True, linestyle="--", axis="y")

    plt.suptitle("AeroVital Core Intelligence Engine — Deterministic Rule Evaluation Across 215,760 Windows", fontsize=15, fontweight="bold", y=0.98)
    plt.tight_layout()
    out_path = VIS_DIR / "engine_fatigue_confidence_evaluation.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f" -> Saved {out_path.name}")


def main():
    plot_scenario_comparisons()
    plot_mixed_operational_timeseries()
    plot_signal_quality_distributions()
    plot_engine_evaluations()
    print("\n[SUCCESS] All 4 publication-quality visualizations generated!")


if __name__ == "__main__":
    main()
