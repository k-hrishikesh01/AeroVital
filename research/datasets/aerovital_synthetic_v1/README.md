# AeroVital Synthetic Physiological Dataset v1 (`aerovital_synthetic_v1`)

A high-fidelity, mathematically consistent, reproducible synthetic physiological dataset designed for research, algorithm development, benchmarking, and offline demonstration of the **AeroVital Aeromedical Vitality & Flight Fatigue Monitoring System**.

---

## 1. Dataset Overview

- **Dataset Identifier:** `aerovital-synthetic-v1`
- **Schema & Generator Version:** `1.0.0`
- **Total Timestamped Records:** 216,000 observations (1.0 Hz nominal cadence)
- **Synthetic Participants:** 30 individual profiles (`SYN-P001` through `SYN-P030`) with personalized resting baselines
- **Flight Sessions:** 60 simulated 1-hour sorties (`SYN-S001` through `SYN-S060`)
- **Random Seed:** `42` (Fixed deterministic seed for exact reproducibility)
- **Operational Isolation:** All records tagged with `data_source="SYNTHETIC"`, `is_synthetic=True`. Fully isolated from production databases and operational flight telemetry.

---

## 2. Experimental Scenarios

The dataset captures five distinct human-factors, physiological, and signal-quality regimes representative of high-performance aviation operations:

| # | Scenario | Participants / Sessions | Flight Regimes | Physiological Characteristics | Telemetry Quality |
| :---: | :--- | :---: | :--- | :--- | :--- |
| **1** | **`NORMAL_BASELINE`** | 6 pilots (12 sessions) | Benign `CRUISE` | Nominal HR ($65.4 \pm 6.9$ bpm) concordant with baseline; healthy HRV ($RMSSD = 40.6$ ms); quiescent cockpit posture. | Pristine ($SQI = 0.999$, missingness $< 0.3\%$). |
| **2** | **`ELEVATED_COGNITIVE_WORKLOAD`** | 6 pilots (12 sessions) | `CLIMB`, `COMBAT_MANEUVER`, `HIGH_G` | Sympathetic arousal: HR surged $+25$ to $+42$ bpm above baseline ($87.9 \pm 10.3$ bpm); vagal suppression ($RMSSD = 15.7$ ms); sustained airframe acceleration up to $4.1$g. | High ($SQI = 0.996$, missingness $\sim 1.0\%$). |
| **3** | **`FATIGUE_PHYSIOLOGICAL`** | 6 pilots (12 sessions) | Extended `CRUISE` | Autonomic fatigue: resting or bradycardic HR ($61.6 \pm 4.2$ bpm) with sporadic micro-arousals; severe vagal exhaustion ($RMSSD = 20.9$ ms, $< 50\%$ of baseline); confirmed nominal $1.0$g load. | Clean ($SQI = 0.998$, missingness $\sim 0.5\%$). |
| **4** | **`DEGRADED_SIGNAL_QUALITY`** | 6 pilots (12 sessions) | `CRUISE` / `DESCENT` | Baseline physiology ($65.9 \pm 5.7$ bpm, $RMSSD = 41.5$ ms) masked by severe sensor artifacts, loose wristband displacement, and packet loss. | Heavily degraded ($SQI = 0.890$, missingness $27.5\%$). |
| **5** | **`MIXED_OPERATIONAL_CONDITIONS`** | 6 pilots (12 sessions) | Multi-phase operational flight profile | Full mission progression: Pre-flight $\to$ Takeoff $\to$ Climb $\to$ Cruise $\to$ Combat Maneuver $\to$ Recovery $\to$ Fatigue Onset $\to$ Approach $\to$ Landing. | Dynamic ($SQI = 0.997$, missingness $\sim 0.7\%$). |

---

## 3. Mathematical Foundations & Physiological Modeling

1. **Autoregressive Beat-to-Beat Interval Modeling:**
   Beat-to-beat intervals (RR intervals / IBI) are simulated using physiological frequency components:
   - **Respiratory Sinus Arrhythmia (RSA):** High-frequency parasympathetic oscillation ($f_{HF} \approx 0.25$ Hz).
   - **Mayer Waves / Baroreflex:** Low-frequency sympathetic/vagal oscillation ($f_{LF} \approx 0.09$ Hz).
   - **Very Low Frequency Drift:** Thermoregulatory and slow metabolic drift ($f_{VLF} \approx 0.005$ Hz).
   - Instantaneous successive differences satisfy $\Delta RR_i \sim \mathcal{N}(0, \text{RMSSD}(t))$.

2. **Strict HR / IBI Concordance:**
   At every observation second, instantaneous pulse rate is calculated directly as:
   $$HR(t) = \text{round}\left(\frac{60000}{\frac{1}{N} \sum_{i=1}^N RR_i}, 1\right)$$
   Empirical validation proves maximum concordance error between $HR$ and $60000 / \text{mean}(RR)$ is $\le 0.050$ bpm across all 216,000 observations.

3. **Hardware Non-Fabrication Guarantee:**
   To maintain empirical integrity with the connected Wear OS hardware layer:
   - Channels not acquired by the hardware (`spo2`, `skin_temperature`, `steps`) are **strictly represented as `null`**, never substituted with arbitrary zeros or artificial values.
   - Sensor dropouts are represented as `null`, never `0`.

---

## 4. AeroVital Intelligence Engine Execution

The dataset was evaluated against the unmodified AeroVital Core Intelligence Engine (`backend/core/pipeline/pipeline.py:AeroVitalPipeline`):
- **Windows Evaluated:** 215,760 sliding temporal windows across 60 sessions.
- **Throughput:** ~3,830 samples/sec (56.35s total runtime).
- **Behavioral Summary:**
  - `NORMAL_BASELINE`: **94.7% NORMAL**, $4.9\%$ INSUFFICIENT_DATA (warmup / brief recovery), $0.4\%$ FATIGUE. Mean confidence = $0.986$.
  - `ELEVATED_COGNITIVE_WORKLOAD`: **66.6% ELEVATED_WORKLOAD**, $33.4\%$ FATIGUE (during interim cruise segments with suppressed RMSSD). Mean confidence = $0.997$.
  - `FATIGUE_PHYSIOLOGICAL`: **99.9% FATIGUE**, $0.1\%$ INSUFFICIENT_DATA. Mean confidence = $0.999$.
  - `DEGRADED_SIGNAL_QUALITY`: **23.1% INSUFFICIENT_DATA (Engine Abstention)**, $74.2\%$ NORMAL, $2.7\%$ FATIGUE. Mean confidence = $0.864$.
  - `MIXED_OPERATIONAL_CONDITIONS`: Dynamic multi-phase tracking: **30.5% ELEVATED_WORKLOAD**, **29.7% NORMAL**, **24.5% INSUFFICIENT_DATA**, **15.3% FATIGUE**. Mean confidence = $0.936$.

---

## 5. Artifact Directory Layout

```
research/datasets/aerovital_synthetic_v1/
├── dataset_manifest.json                 # Checksums, sizes, and metadata
├── participants.json                     # 30 synthetic pilot profiles & baselines
├── sessions.json                         # 60 session definitions & empirical statistics
├── synthetic_physiological_dataset.csv   # Tabular dataset (35.08 MB)
├── synthetic_physiological_dataset.jsonl # Line-delimited JSON (105.91 MB)
├── synthetic_physiological_dataset.json  # Array JSON (106.11 MB)
├── data_dictionary.md                    # Complete schema and column documentation
├── statistical_summary.md                # Empirical statistics by scenario
├── validation_report.md                  # Results of 9 automated validation audits
├── engine_execution_results.json         # Raw engine outputs for all 60 sessions
├── engine_execution_report.md            # Scenario-level intelligence engine findings
├── generate_dataset.py                   # Reproducible generator script (seed=42)
├── validate_dataset.py                   # Automated validation suite
├── run_engine_evaluation.py              # Core engine execution runner
├── generate_visualizations.py            # High-resolution figure generator
├── visualizations/                       # Publication-quality charts (PNG)
│   ├── scenario_comparison_hr_hrv.png
│   ├── mixed_operational_timeseries.png
│   ├── signal_quality_distributions.png
│   └── engine_fatigue_confidence_evaluation.png
└── README.md                             # This document
```

---

## 6. How to Reproduce

All artifacts are 100% reproducible via Python in the repository virtual environment:

```bash
# 1. Regenerate Dataset (Deterministic Seed 42)
.venv/bin/python research/datasets/aerovital_synthetic_v1/generate_dataset.py

# 2. Run Automated Validation Suite (9 Audits)
.venv/bin/python research/datasets/aerovital_synthetic_v1/validate_dataset.py

# 3. Execute AeroVital Core Intelligence Engine
.venv/bin/python research/datasets/aerovital_synthetic_v1/run_engine_evaluation.py

# 4. Generate Visualizations
.venv/bin/python research/datasets/aerovital_synthetic_v1/generate_visualizations.py
```

---

## 7. Assumptions & Research Limitations

> [!WARNING]
> **Aviation Human Factors & Clinical Safety Disclaimers:**
> 1. **Synthetic Nature:** This dataset is mathematically generated for software architecture verification, telemetry pipeline testing, and interface development. It does not contain actual human flight test data.
> 2. **Experimental Scenario Labels:** Labels (`NORMAL_BASELINE`, `FATIGUE_PHYSIOLOGICAL`, etc.) describe the generative scenario rules; they do not represent independently validated medical or clinical ground truth.
> 3. **Non-Certification:** Neither this dataset nor the accompanying AeroVital Core Intelligence Engine is certified as a medical diagnostic device or flight safety clearance system.
