# AeroVital Synthetic Physiological Dataset v1 — Data Dictionary

**Dataset Identifier:** `aerovital-synthetic-v1`  
**Schema Version:** `1.0.0`  
**Generator Version:** `1.0.0`  
**Nominal Sampling Rate:** 1.0 Hz (1 observation / second)  
**Total Records:** 216,000 observations (60 sessions $\times$ 3,600 seconds)  
**Operational Isolation:** Fully isolated research dataset (`data_source="SYNTHETIC"`, `is_synthetic=True`)

---

## 1. Primary Record Schema

The primary tabular dataset is provided in `synthetic_physiological_dataset.csv`, `synthetic_physiological_dataset.jsonl`, and `synthetic_physiological_dataset.json`.

| Field Name | Data Type | Units / Range | Nullable | Source / Acquisition | Definition & Aviation Human Factors Context |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `timestamp` | String (ISO 8601) | UTC timestamp | **No** | System Clock | Canonical UTC timestamp of the 1 Hz observation. Strictly monotonic at 1.0s increments within each session. |
| `participant_id` | String | `SYN-P001` – `SYN-P030` | **No** | Metadata Identifier | Synthetic participant identifier linked to an individual resting baseline profile in `participants.json`. |
| `session_id` | String | `SYN-S001` – `SYN-S060` | **No** | Metadata Identifier | Unique flight session identifier linked to session-level parameters in `sessions.json`. Exactly 3,600 observations per session. |
| `scenario` | String (Enum) | 5 scenarios | **No** | Experimental Design | Experimental condition label: `NORMAL_BASELINE`, `ELEVATED_COGNITIVE_WORKLOAD`, `FATIGUE_PHYSIOLOGICAL`, `DEGRADED_SIGNAL_QUALITY`, or `MIXED_OPERATIONAL_CONDITIONS`. |
| `heart_rate` | Float | Beats/Min (BPM) [40.0, 185.0] | **Yes** | Wear OS Optical PPG | Instantaneous/windowed pulse rate. Represented as `null` during sensor dropouts and disconnects. **Never represented as zero.** Mathematically concordant with `60000 / mean(rr_interval)`. |
| `rr_interval` | Float / List[Float] | Milliseconds (ms) [300.0, 1500.0] | **Yes** | Wear Health Services / IBI | Beat-to-beat intervals (RR / IBI) completed during the observation second. Semicolon-delimited in CSV; array in JSON/JSONL. Null during dropouts. |
| `spo2` | Float | Percentage (0 – 100%) | **Yes** | Hardware Channel | **Strictly Null.** Current Wear OS acquisition hardware does not continuously stream SpO2 during active flight. Not fabricated. |
| `skin_temperature` | Float | Degrees Celsius (°C) | **Yes** | Hardware Channel | **Strictly Null.** Not provided by current acquisition hardware. Non-fabrication guarantee enforced. |
| `activity_level` | String (Enum) | Categorical string | **No** | Wearable Motion Classifier | Classification of physical limb activity: `REST`, `MODERATE`, `HIGH_MANEUVER`, `STATIONARY`, or `UNKNOWN`. |
| `steps` | Integer | Count | **Yes** | Pedometer | **Strictly Null.** Quiescent cockpit seat protocol; pedometer step counts are not relevant to fixed-wing pilot vitality. |
| `accel_x` | Float | Acceleration (g) | **No** | Wearable 3-Axis IMU | Simulated lateral acceleration of the pilot's wrist relative to the cockpit frame. |
| `accel_y` | Float | Acceleration (g) | **No** | Wearable 3-Axis IMU | Simulated longitudinal acceleration (fore/aft) of the pilot's wrist. |
| `accel_z` | Float | Acceleration (g) | **No** | Wearable 3-Axis IMU | Simulated vertical acceleration of the pilot's wrist, reflecting earth gravity + external airframe G-load. |
| `battery_level` | Float | Percentage [5.0, 100.0%] | **No** | Device Power API | Simulated smartwatch battery state discharging nominally at ~8.5% per flight hour. |
| `mission_phase` | String (Enum) | Operational Phase Enum | **No** | Avionics / Flight Plan | Current flight regime: `PRE_FLIGHT`, `TAXI`, `TAKEOFF`, `CLIMB`, `CRUISE`, `COMBAT_MANEUVER`, `HIGH_G`, `DESCENT`, `APPROACH`, `LANDING`, `POST_FLIGHT`. |
| `external_g_load` | Float | Airframe G-force (g) [0.9, 4.5] | **No** | Aircraft Avionics Bus | External normal acceleration (Nz) measured by the aircraft flight data recorder. Used by the AeroVital engine to separate physiological workload from baseline fatigue. |
| `flight_duration_sec` | Integer | Seconds [0, 3599] | **No** | Flight Data Bus | Mission elapsed time from session start. |
| `data_source` | String | Constant `"SYNTHETIC"` | **No** | Provenance Header | Explicit isolation tag ensuring synthetic research records are never mixed with measured operational flight records. |
| `dataset_id` | String | Constant `"aerovital-synthetic-v1"` | **No** | Provenance Header | Master dataset identifier. |
| `is_synthetic` | Boolean | Constant `True` | **No** | Provenance Header | Boolean flag preventing ingestion into production databases. |

---

## 2. Participant Baseline Schema (`participants.json`)

| Field Name | Data Type | Units / Description |
| :--- | :--- | :--- |
| `pilot_id` | String | Unique synthetic participant identifier (`SYN-P001` – `SYN-P030`). |
| `callsign` | String | Synthetic tactical callsign (`VITAL-01` – `VITAL-30`). |
| `age` | Integer | Participant age in years (Range: 26 – 48). |
| `baseline_version` | String | Versioned calibration identifier (e.g. `CAL-2026-001`). |
| `calibration_timestamp` | String (ISO 8601) | Timestamp of resting physiological baseline calibration. |
| `resting_heart_rate` | Float (BPM) | Resting baseline heart rate established during pre-flight protocol (Range: 54.0 – 78.0 bpm). |
| `baseline_rmssd` | Float (ms) | Resting baseline RMSSD heart rate variability (Range: 30.0 – 72.0 ms). |
| `baseline_sdnn` | Float (ms) | Resting baseline standard deviation of NN intervals (Range: 41.0 – 95.0 ms). |
| `baseline_mean_rr` | Float (ms) | Resting baseline mean RR interval ($60000 / \text{resting\_hr}$). |
| `calibration_duration_sec` | Integer | Duration of resting calibration (600 seconds = 10 minutes). |
| `is_calibrated` | Boolean | Calibration validity flag (`True`). |
| `assigned_scenario_group` | String | Assigned research scenario group. |

---

## 3. Session Metadata Schema (`sessions.json`)

| Field Name | Data Type | Units / Description |
| :--- | :--- | :--- |
| `session_id` | String | Unique session identifier (`SYN-S001` – `SYN-S060`). |
| `participant_id` | String | Associated participant ID. |
| `scenario` | String | Experimental scenario condition. |
| `start_time` / `end_time` | String (ISO 8601) | UTC session boundaries. |
| `duration_sec` | Integer | Session length (3,600 seconds). |
| `total_observations` | Integer | Total 1 Hz observation slots (3,600). |
| `valid_observations` | Integer | Non-null physiological observation count. |
| `missing_observations` | Integer | Dropped / null observation count. |
| `missing_rate_pct` | Float (%) | Telemetry packet dropout rate. |
| `hr_mean` / `hr_min` / `hr_max` | Float (BPM) | Empirical heart rate statistics for the session. |
| `empirical_rmssd_ms` | Float (ms) | Actual root mean square of successive differences computed from raw RR intervals. |
| `empirical_sdnn_ms` | Float (ms) | Standard deviation of valid RR intervals. |
| `empirical_pnn50_pct` | Float (%) | Percentage of successive interval differences exceeding 50 ms. |
