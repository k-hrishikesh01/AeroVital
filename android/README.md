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

**IMPLEMENTED (A1, A2, A3, A4, A5, A6, A7):**
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
- [x] Phone → Django Authenticated Telemetry Ingestion (A5)
    - Clean HTTP client abstraction (`DjangoTelemetryClient`) sending CanonicalTelemetry to `POST /api/v1/telemetry/`
    - Token-authenticated with `Authorization: Token <token>` via `TokenProvider` dependency boundary
    - Strict credential hygiene: Authorization headers redacted from logs, tokens never logged or hardcoded
    - Configurable backend base URL (no hardcoded localhost or production endpoints)
    - Explicit failure semantics distinguishing success, auth failure, client failure, server failure, network failure, and malformed payload
    - Integration coordinator (`PhoneTelemetryIngestionHandler`) extracting `CanonicalTelemetry` from validated `TransportEnvelope`s
- [x] Durable Store-and-Forward Telemetry Queue (A6)
    - Crash-safe, durable queue store (`DurableTelemetryQueueStore`) persisting individual atomic JSON records in phone storage
    - Explicit queue record contract (`DurableQueueRecord`) preserving exact A2 envelope fields, identity, and delivery lifecycle metadata
    - Atomic file operations (`.tmp` write followed by atomic rename) guaranteeing durability across process crashes, restarts, and phone reboots
    - Deterministic queue ordering (`RECORD_ORDER_COMPARATOR`: observation timestamp ASC, sequenceNumber ASC, enqueueTime ASC, messageId ASC)
    - Delivery worker (`TelemetryDeliveryCoordinator`) reading pending records in deterministic order and transmitting via existing A5 client
    - Bounded exponential retry policy (`QueueRetryPolicy`: 1s initial, 2.0x multiplier, 60s max, 5 attempts max, 10,000 capacity)
    - Transient failure retention (network/5xx) with exponential backoff
    - Authentication failure isolation (`AUTH_BLOCKED` on 401/403) pausing delivery until re-authentication without infinite retries
    - Non-retryable error dead-lettering (`FAILED_TERMINAL` on 4xx/malformed/max retries) without silent data deletion
    - Enqueue before delivery guarantee in `PhoneTelemetryIngestionHandler`
- [x] Physical End-to-End Integration & Hardware Diagnostic Surface (A7)
    - Watch Runtime Wiring (`WatchAcquisitionCoordinator`) managing `BODY_SENSORS` permission, sensor adapters, 1-second batching, and `TelemetryTransportHandoff`
    - Watch Diagnostic Screen (`MainActivity`) with runtime permission prompt, live HR/Accel/Gyro sensor observations, phone node discovery, and packet transmission tracking
    - Phone Service-Level Wiring (`WearTransportReceiver.getOrInitHandler`) enabling background message reception and ingestion even if MainActivity is not active
    - Phone Network Security Configuration (`network_security_config.xml`) permitting cleartext HTTP strictly for development loopbacks (`10.0.2.2`, `127.0.0.1`, `localhost`)
    - Dynamic Development Backend Configuration (`DevBackendConfig`) supporting ADB reverse tethering (`http://127.0.0.1:8000/`) and emulator (`http://10.0.2.2:8000/`)
    - Phone Diagnostic Screen (`PhoneDiagnosticScreen`) providing live transport message tracking, read-only queue observability (`QueueDiagnosticSummary`), and manual drain trigger

**NOT YET IMPLEMENTED:**
- [ ] Additional platform/vendor health APIs, if required after physical hardware capability verification
- [ ] Real-time operational context tagging (G-load, flight phase)
- [ ] Operational contexts synchronization

---

## Technical Boundaries

- **A7 enables physical software pipeline execution and diagnostic observability.** The watch runtime wires sensors through 1Hz canonical telemetry handoff to the transport sender, and the phone receiver eagerly routes background messages into the durable store-and-forward queue for delivery to Django. Diagnostic surfaces provide live hardware validation without modifying upstream contracts or inventing Android-side inference.
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
