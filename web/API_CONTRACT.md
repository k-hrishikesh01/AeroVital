# AeroVital Frontend-Backend API Contract & Mapping

This document specifies the exact REST API contracts implemented by the Django backend on `main` and consumed by the React/Vite dashboard (`web/`).

All endpoints are versioned under `/api/v1/`.

---

## 1. Authentication Endpoints

### 1.1 Obtain Auth Token
* **Endpoint:** `POST /api/v1/auth/token/`
* **Purpose:** Authenticate pilot or flight surgeon credentials and obtain an API authorization token.
* **Authentication Requirement:** Unauthenticated (`AllowAny`)
* **Request Body:**
  ```json
  {
    "username": "pilot_username",
    "password": "pilot_password"
  }
  ```
* **Response Status:** `200 OK` / `401 Unauthorized` / `400 Bad Request`
* **Response Fields:**
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `token` | `string` | Django REST Framework Token string used in `Authorization: Token <key>` |
  | `user_id` | `integer` | Django User primary key |
  | `username` | `string` | User login name |
  | `pilot` | `object \| null` | Linked pilot profile record (if pilot account) |
* **Frontend Presentation Mapping:**
  * Stored in React authentication state (`useAuth`) and `localStorage` (`aerovital_auth_token`).
  * Attached as HTTP header `Authorization: Token <token>` on all subsequent requests.

### 1.2 Current User Profile
* **Endpoint:** `GET /api/v1/auth/me/`
* **Purpose:** Validate existing token session and fetch pilot context.
* **Authentication Requirement:** Authenticated (`IsAuthenticated`, Token header)
* **Response Fields:**
  | Field | Type | Description |
  | :--- | :--- | :--- |
  | `user_id` | `integer` | User primary key |
  | `username` | `string` | Username |
  | `email` | `string` | Email address |
  | `pilot` | `object \| null` | Nested pilot profile (ID, pilot_code, name, age, sex, etc.) |
* **Frontend Presentation Mapping:**
  * Displays pilot name and code in Dashboard Header and Profile Drawer.

### 1.3 Logout
* **Endpoint:** `POST /api/v1/auth/logout/`
* **Purpose:** Invalidate current user auth token on the server.
* **Authentication Requirement:** Authenticated
* **Response:** `{"detail": "Successfully logged out."}`

---

## 2. Intelligence & Fatigue Estimation Endpoints

### 2.1 Current State
* **Endpoint:** `GET /api/v1/intelligence/current-state/`
* **Purpose:** Real-time consolidated telemetry freshness, fatigue state, confidence, SQI, and mission info.
* **Authentication Requirement:** Authenticated (Pilot-scoped)
* **Query Parameters:** `mission` (UUID, optional), `pilot` (UUID, optional, staff-only override)
* **Response Fields:**
  | Field | Type | Description | Frontend Mapping |
  | :--- | :--- | :--- | :--- |
  | `current_state` | `string` | Discrete fatigue classification (`NORMAL`, `ELEVATED_WORKLOAD`, `FATIGUE`, `INSUFFICIENT_DATA`) | Main condition badge & card border styling |
  | `fatigue_score` | `float \| null` | Latent fatigue estimate `[0.0, 1.0]` (null if `INSUFFICIENT_DATA`) | Rendered as percentage e.g. `24%` or `N/A` |
  | `confidence` | `float` | Metric `[0.0, 1.0]` representing completeness & fidelity | Rendered as Confidence percentage e.g. `85%` |
  | `overall_sqi` | `float` | Composite Signal Quality Index `[0.0, 1.0]` | Rendered as Signal Quality percentage e.g. `92%` |
  | `dominant_factors` | `string[]` | Physiological and operational factors contributing to state | Displayed in Factors bulleted card |
  | `evidence` | `object` | Detailed feature values and heuristics | Shown in technical details disclosure |
  | `baseline_version` | `string \| null`| Version ID of pilot baseline used | Shown in baseline metadata badge |
  | `timestamp` | `string (ISO)` | Timestamp of current estimate | Displayed as "Last estimated: HH:MM:SS" |
  | `last_telemetry_timestamp` | `string (ISO)`| Timestamp of most recent telemetry sample | Freshness comparison |
  | `freshness_sec` | `float \| null` | Seconds elapsed since last telemetry packet | Used to flag `LIVE` (<30s) or `STALE` (>30s) status |
  | `mission` | `object \| null` | Active mission context (`id`, `code`, `status`, `phase`, `g_load`) | Flight tag in Header & G-Force indicator |

### 2.2 Historical State Estimates
* **Endpoint:** `GET /api/v1/intelligence/estimates/` (or `/api/v1/intelligence/state-estimates/`)
* **Purpose:** Time-series sequence of past fatigue estimations for trend timeline.
* **Authentication Requirement:** Authenticated (Pilot-scoped)
* **Query Parameters:** `mission` (UUID), `fatigue_state` (string), `limit` (integer, max 500)
* **Response Fields:** Array of state estimate objects:
  * `timestamp` (ISO datetime)
  * `fatigue_state` (`NORMAL` \| `ELEVATED_WORKLOAD` \| `FATIGUE` \| `INSUFFICIENT_DATA`)
  * `fatigue_score` (float 0.0–1.0 or null)
  * `confidence` (float 0.0–1.0)
  * `overall_sqi` (float 0.0–1.0)
  * `dominant_factors` (string[])
* **Frontend Presentation Mapping:**
  * Rendered in **Flight Vitality & Telemetry Timeline** chart tracking fatigue trends over flight duration.

---

## 3. Telemetry Endpoints

### 3.1 Time-Series Telemetry
* **Endpoint:** `GET /api/v1/telemetry/`
* **Purpose:** Query raw physiological samples for live biometric stream.
* **Authentication Requirement:** Authenticated (Pilot-scoped)
* **Query Parameters:** `mission` (UUID), `device` (UUID), `limit` (integer, default 100)
* **Response Fields:** Array of telemetry sample records:
  | Field | Type | Description | Frontend Mapping |
  | :--- | :--- | :--- | :--- |
  | `timestamp` | `string (ISO)` | UTC sample capture time | X-axis timestamp in charts & table |
  | `heart_rate` | `float \| null` | Heart rate in beats per minute | Heart Rate card & rolling trend |
  | `rr_interval` | `float \| null` | R-to-R interval in milliseconds | Biometric stream & table |
  | `spo2` | `float \| null` | Blood oxygen percentage | SpO2 indicator (or "N/A" if null) |
  | `skin_temperature` | `float \| null` | Peripheral temperature in °C | Atmospheric/Physiological strip |
  | `activity_level` | `string \| null`| Activity classification | Telemetry details strip |
  | `steps` | `integer \| null`| Accumulated steps | Details strip |
  | `accel_x, accel_y, accel_z` | `float \| null` | Accelerometer axes in Gs | Motion context |
  | `battery_level` | `integer \| null`| Wearable battery percentage | Device health badge |

### 3.2 Signal Quality Index (SQI)
* **Endpoint:** `GET /api/v1/telemetry/quality/` (or `/api/telemetry/signal-quality/`)
* **Purpose:** Inspect sensor noise, artifacting, and channel reliability.
* **Authentication Requirement:** Authenticated (Pilot-scoped)
* **Response Fields:** Array of SQI assessment records:
  * `timestamp` (ISO datetime)
  * `overall_sqi` (float 0.0–1.0)
  * `is_telemetry_acceptable` (boolean)
  * `motion_corruption_index` (float 0.0–1.0)
  * `channels` (object e.g. `{"ecg": 0.95, "ppg": 0.88}`)
* **Frontend Presentation Mapping:**
  * Displayed in Signal Quality card and channel health breakdown.

### 3.3 Feature Windows
* **Endpoint:** `GET /api/v1/telemetry/features/`
* **Purpose:** Read aggregated time-window HRV metrics extracted by Core cleaner/feature pipeline.
* **Authentication Requirement:** Authenticated (Pilot-scoped)
* **Response Fields:**
  * `mean_hr`, `min_hr`, `max_hr`, `hr_std`
  * `mean_rr_ms`, `sdnn_ms`, `rmssd_ms`, `pnn50_percent`
  * `hr_deviation_from_baseline`, `hrv_rmssd_ratio_to_baseline`
* **Frontend Presentation Mapping:**
  * HRV RMSSD and SDNN display panels.

---

## 4. Alerts Endpoints

### 4.1 Alert List
* **Endpoint:** `GET /api/v1/alerts/`
* **Purpose:** List safety notifications, high-workload advisories, and sensor alerts.
* **Authentication Requirement:** Authenticated (Pilot-scoped)
* **Query Parameters:** `mission` (UUID), `severity` (`INFO`, `WARNING`, `CRITICAL`), `unacknowledged` (`true`/`false`)
* **Response Fields:**
  | Field | Type | Description | Frontend Mapping |
  | :--- | :--- | :--- | :--- |
  | `id` | `UUID` | Alert unique identifier | React key & acknowledge action target |
  | `alert_type` | `string` | System alert classification | Title in Alert card |
  | `severity` | `string` | `INFO` \| `WARNING` \| `CRITICAL` | Color badge (Blue, Amber, Red) |
  | `message` | `string` | Human-readable alert explanation | Description in Alert card |
  | `trigger_state`| `string` | State causing alert | Trigger context tag |
  | `confidence` | `float` | Estimation confidence when alert fired | Confidence badge |
  | `acknowledged`| `boolean` | Whether operator acknowledged | Filter state |
  | `timestamp` | `string (ISO)` | Alert trigger time | Relative time e.g. "2 min ago" |

### 4.2 Acknowledge Alert
* **Endpoint:** `POST /api/v1/alerts/<uuid:id>/acknowledge/`
* **Purpose:** Mark an active safety alert as acknowledged by the flight crew.
* **Authentication Requirement:** Authenticated (Pilot-scoped or staff)
* **Response:** Updated Alert object with `acknowledged = true` and `acknowledged_at = ISO timestamp`.

---

## 5. Missions & Pilots Endpoints

### 5.1 Missions
* **Endpoint:** `GET /api/v1/missions/`
* **Purpose:** List pilot missions and active flight phase.
* **Authentication Requirement:** Authenticated (Pilot-scoped)
* **Response Fields:**
  * `id` (UUID)
  * `mission_code` (e.g. `"AV-409"`)
  * `mission_type` (e.g. `"COMMERCIAL"`)
  * `current_phase` (e.g. `"CRUISE"`, `"CLIMB"`, `"APPROACH"`)
  * `external_g_load` (float)
  * `start_time`, `end_time`, `status` (`IN_PROGRESS`, `COMPLETED`)

### 5.2 Pilots
* **Endpoint:** `GET /api/v1/pilots/`
* **Purpose:** List pilot profiles (staff or authorized operator).
* **Authentication Requirement:** Authenticated

---

## 6. Critical Architecture Constraints

1. **Presentation Layer Only:** The React dashboard never derives or calculates fatigue state, confidence, or SQI. It consumes backend-provided calculations directly.
2. **Enum Fidelity:** The dashboard strictly utilizes backend vocabulary (`NORMAL`, `ELEVATED_WORKLOAD`, `FATIGUE`, `INSUFFICIENT_DATA`).
3. **No Synthetic Telemetry:** Real endpoints are consumed. If data is absent, the UI explicitly renders `N/A` or empty/insufficient-data states without generating fake random data.
