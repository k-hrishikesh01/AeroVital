# AeroVital — Android & Wear OS Application

> **STATUS: IN PROGRESS / FOUNDATION IMPLEMENTED**  
> **Classification:** Engineering Prototype / Gateway Scaffold  
> **Target Devices:** Samsung Galaxy Watch (Wear OS 4+) & Android Mobile Gateway  

---

## Overview

This directory contains the AeroVital wearable telemetry client and phone companion.

**This component is currently under active development. Real sensor integration and telemetry streaming are NOT YET COMPLETE.**

---

## Planned Architecture

```
Galaxy Watch (Wear OS)
   ├── Sensor Acquisition / Adapter Layer
   ├── Local Sensor Sampling & Monotonic Buffering
   └── Wear Transport Layer (Play Services)
         ↓
Android Companion Phone
   ├── Wear Transport Receiver
   ├── Pilot Authentication (Token Auth)
   ├── Store-and-Forward Offline Buffer
   └── HTTPS REST Ingestion Adapter
         ↓
Django REST API (`/api/v1/telemetry/`)
```

---

## Current Implementation State

**IMPLEMENTED (A1, A2, A3, A4):**
- [x] Initial Android Studio / Gradle Kotlin DSL build configuration (`build.gradle.kts`, `settings.gradle.kts`)
- [x] Django REST Authentication (Token-based) integration on Phone
- [x] Secure Android Keystore-backed credential storage
- [x] Wear OS ↔ Android Phone transport foundation (A2)
- [x] Transport Envelope schema (versioned, uniquely identified, timestamped JSON)
- [x] Envelope validation, error handling, duplicate filtering, and staleness detection
- [x] Unit test suites for authentication and transport boundaries
- [x] Wear OS Sensor Acquisition Layer (A3)
    - Normalized sensor observations
    - Android SensorManager API integration
    - Heart Rate, Accelerometer, Gyroscope adapters
    - Explicitly unavailable channels representation (SpO2, Skin Temp, RR Interval)
- [x] Canonical Telemetry Mapping & Watch → Phone Handoff (A4)
    - Canonical AeroVital telemetry representation (`CanonicalTelemetry`) matching backend contract
    - Telemetry mapper (`TelemetryMapper`) converting A3 observations to canonical schema
    - Timestamp preservation from originating hardware sensor observations
    - Partial telemetry support (unobserved channels strictly null; never zero-filled or fabricated)
    - Integration with existing A2 `TransportEnvelope` and `WearTransportSender` (`TelemetryTransportHandoff`)

**NOT YET IMPLEMENTED:**
- [ ] Additional platform/vendor health APIs, if required after physical hardware capability verification
- [ ] Offline store-and-forward buffering
- [ ] Django telemetry ingestion (Phone → Django REST API)
- [ ] Real-time operational context tagging (G-load, flight phase)
- [ ] Operational contexts synchronization

---

## Technical Boundaries

- **A4 prepares canonical telemetry for A2 transport.** Real sensor observations are mapped to canonical telemetry and enveloped for Watch → Phone transport. Phone → Django REST ingestion is not yet implemented.
- **Fatigue Inference:** The Android application handles sensor acquisition and data transport only. Fatigue estimation is performed strictly upstream by the AeroVital Core.
- **Database:** No direct PostgreSQL access is permitted from Android. The Django backend API serves as the sole system of record.
- **Firebase:** Strictly excluded by design requirements.

---

## Sensor Layer Details (A3)

**Sensors Investigated:**
Heart Rate, Accelerometer, Gyroscope, RR Interval, SpO2, Skin Temperature.

**APIs Actually Used:**
Standard Android `SensorManager`. Third-party dependencies (like `androidx.health.services`) have intentionally been avoided at this stage to establish a clean compatibility baseline.

**Permissions Required:**
`android.permission.BODY_SENSORS`

**Channels Available Through Implemented Application:**
- `SensorType.HEART_RATE` (bpm)
- `SensorType.ACCELEROMETER` (m/s²)
- `SensorType.GYROSCOPE` (rad/s)

**Channels Unavailable Through Implemented Application:**
- `SensorType.RR_INTERVAL`
- `SensorType.SPO2`
- `SensorType.SKIN_TEMPERATURE`
*(Represented explicitly as `UNAVAILABLE` rather than fabricating values, as these channels are not exposed through the standard SensorManager acquisition layer.)*

**Timestamp Behavior:**
Preserves original hardware nanosecond timestamps (`SensorEvent.timestamp`) indicating uptime since boot.

**Sampling Behavior:**
Uses `SENSOR_DELAY_NORMAL`. No manual imputation, interpolation, or smoothing is performed by the adapters.

**Lifecycle Behavior:**
Adapters implement explicit `start()` and `stop()` mechanisms, cleaning up listeners immediately to prevent memory/battery leaks.

**Known Galaxy Watch Capability Limitations:**
Physical Galaxy Watch capability verification is still pending. The current implementation exposes only the channels available through the implemented `SensorManager` acquisition layer: heart rate, accelerometer, and gyroscope. RR interval, SpO2, and skin temperature are currently unavailable through this implementation. Additional platform/vendor APIs may be evaluated later if required by verified hardware capabilities.
