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
   ├── Samsung Privileged Health SDK (PPG, ECG, SpO2, Accelerometer)
   ├── Local Sensor Sampling & Monotonic Buffering
   └── Wear Transport Layer (Play Services)
         ↓
Android Companion Phone
   ├── Wear Transport Receiver
   ├── Pilot Authentication (Token Auth)
   ├── Store-and-Forward Offline Cache (Room DB)
   └── HTTPS REST Ingestion Adapter
         ↓
Django REST API (`/api/v1/telemetry/`)
```

---

## Current Implementation State

**IMPLEMENTED (A1 & A2):**
- [x] Initial Android Studio / Gradle Kotlin DSL build configuration (`build.gradle.kts`, `settings.gradle.kts`)
- [x] Django REST Authentication (Token-based) integration on Phone
- [x] Secure Android Keystore-backed credential storage
- [x] Wear OS ↔ Android Phone transport foundation
- [x] Transport Envelope schema (versioned, uniquely identified, timestamped JSON)
- [x] Envelope validation, error handling, duplicate filtering, and staleness detection
- [x] Unit test suites for authentication and transport boundaries

**NOT YET IMPLEMENTED:**
- [ ] Real Samsung sensor acquisition (PPG, SpO2, HR, etc.)
- [ ] Physiological sensor adapters
- [ ] Offline store-and-forward (Room DB)
- [ ] Django telemetry ingestion (Watch → Phone → Django)
- [ ] Real-time operational context tagging (G-load, flight phase)
- [ ] Operational contexts synchronization

---

## Technical Boundaries

- **A2 establishes WATCH → PHONE transport only.** Real sensor acquisition and WATCH → PHONE → DJANGO telemetry ingestion are not yet implemented.
- **Fatigue Inference:** The Android application acts strictly as a data transport layer. Fatigue estimation is performed strictly upstream by the AeroVital Core.
- **Database:** No direct PostgreSQL access is permitted from Android. The Django backend API serves as the sole system of record.
- **Firebase:** Strictly excluded by design requirements.
