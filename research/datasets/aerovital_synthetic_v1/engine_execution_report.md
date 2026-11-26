# AeroVital Core Intelligence Engine Execution Report

**Execution Timestamp:** `2026-11-25T13:44:16.890891+00:00`  
**Engine Orchestrator:** `AeroVitalPipeline` (v1.0.0)  
**Dataset Evaluated:** `aerovital-synthetic-v1` (60 sessions, 216,000 observations)  
**Total Windows Evaluated:** 215,760  
**Execution Throughput:** 3833.5 samples/sec (56.35s total run time)  

> [!NOTE]
> **Provisional Research Disclaimer:** Synthetic scenario labels represent experimental configurations, not clinical ground truth. The AeroVital Core Intelligence Engine operates with strict non-imputation and rule-based structural evidence evaluation. These results demonstrate deterministic pipeline behavior, not clinical diagnostic accuracy or operational pilot safety certification.

## Scenario Evaluation Breakdown

| Scenario | Windows | NORMAL (%) | ELEVATED_WORKLOAD (%) | FATIGUE (%) | INSUFFICIENT_DATA (%) | Mean Conf | Mean SQI |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NORMAL_BASELINE** | 43,152 | 94.36% | 0.0% | 0.06% | 5.57% | 0.985 | 0.999 |
| **ELEVATED_COGNITIVE_WORKLOAD** | 43,152 | 0.0% | 66.63% | 33.37% | 0.0% | 0.997 | 0.996 |
| **FATIGUE_PHYSIOLOGICAL** | 43,152 | 0.0% | 0.0% | 99.97% | 0.03% | 0.999 | 0.998 |
| **DEGRADED_SIGNAL_QUALITY** | 43,152 | 74.4% | 0.0% | 2.77% | 22.83% | 0.863 | 0.886 |
| **MIXED_OPERATIONAL_CONDITIONS** | 43,152 | 29.52% | 30.48% | 15.65% | 24.35% | 0.937 | 0.997 |


## Representative Engine Outputs by State

### State: `FATIGUE`
- **Triggering Scenario:** `NORMAL_BASELINE` (Session `SYN-S001`)
- **Confidence:** `1.0` | **Overall SQI:** `1.0`
- **Baseline Version Used:** `CAL-2026-001`
- **Dominant Rationale Factors:**
  - *Depressed beat-to-beat variability (RMSSD ratio: 0.63)*
  - *Confirmed low G-load (1.0g)*
  - *Confirmed benign flight phase (CRUISE)*

### State: `INSUFFICIENT_DATA`
- **Triggering Scenario:** `NORMAL_BASELINE` (Session `SYN-S001`)
- **Confidence:** `0.75` | **Overall SQI:** `1.0`
- **Baseline Version Used:** `CAL-2026-001`
- **Dominant Rationale Factors:**
  - *Evidence insufficient or unconfirmed for any operational state*

### State: `NORMAL`
- **Triggering Scenario:** `NORMAL_BASELINE` (Session `SYN-S001`)
- **Confidence:** `1.0` | **Overall SQI:** `1.0`
- **Baseline Version Used:** `CAL-2026-001`
- **Dominant Rationale Factors:**
  - *Positive baseline concordance: HR and RMSSD within nominal limits*

### State: `ELEVATED_WORKLOAD`
- **Triggering Scenario:** `ELEVATED_COGNITIVE_WORKLOAD` (Session `SYN-S013`)
- **Confidence:** `1.0` | **Overall SQI:** `1.0`
- **Baseline Version Used:** `CAL-2026-007`
- **Dominant Rationale Factors:**
  - *Elevated heart rate (+20.4 BPM relative to baseline)*
  - *High-workload flight phase (CLIMB)*

## Top Dominant Contributing Factors Across Scenarios

### NORMAL_BASELINE
- **Positive baseline concordance: HR and RMSSD within nominal limits** (40,720 windows)
- **Evidence insufficient or unconfirmed for any operational state** (2,404 windows)
- **Confirmed low G-load (1.0g)** (28 windows)
- **Confirmed benign flight phase (CRUISE)** (28 windows)
- **Depressed beat-to-beat variability (RMSSD ratio: 0.70)** (4 windows)

### ELEVATED_COGNITIVE_WORKLOAD
- **High-workload flight phase (COMBAT_MANEUVER)** (21,600 windows)
- **Confirmed low G-load (1.1g)** (14,400 windows)
- **Confirmed benign flight phase (CRUISE)** (14,400 windows)
- **High-workload flight phase (CLIMB)** (7,152 windows)
- **High G-load (3.0g)** (1,980 windows)

### FATIGUE_PHYSIOLOGICAL
- **Confirmed benign flight phase (CRUISE)** (43,139 windows)
- **Confirmed low G-load (1.0g)** (43,031 windows)
- **Depressed beat-to-beat variability (RMSSD ratio: 0.45)** (3,026 windows)
- **Depressed beat-to-beat variability (RMSSD ratio: 0.44)** (2,899 windows)
- **Depressed beat-to-beat variability (RMSSD ratio: 0.46)** (2,844 windows)

### DEGRADED_SIGNAL_QUALITY
- **Positive baseline concordance: HR and RMSSD within nominal limits** (32,104 windows)
- **Evidence insufficient or unconfirmed for any operational state** (8,764 windows)
- **Confirmed benign flight phase (CRUISE)** (1,195 windows)
- **Physiological sensor channels unreliable or motion-corrupted** (929 windows)
- **Confirmed low G-load (1.0g)** (498 windows)

### MIXED_OPERATIONAL_CONDITIONS
- **Positive baseline concordance: HR and RMSSD within nominal limits** (12,737 windows)
- **High-workload flight phase (COMBAT_MANEUVER)** (8,208 windows)
- **Confirmed benign flight phase (CRUISE)** (6,708 windows)
- **Evidence insufficient or unconfirmed for any operational state** (5,761 windows)
- **Confirmed low G-load (1.0g)** (5,062 windows)

