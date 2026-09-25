# AeroVital — Android & Wear OS Application

> **STATUS: IN PROGRESS / UNIMPLEMENTED**  
> **Classification:** Engineering Prototype Stub / Initial Scaffold  
> **Target Devices:** Samsung Galaxy Watch (Wear OS 4+) & Android Mobile Gateway  

---

## Overview

This directory contains the initial Gradle scaffold and Wear OS Compose project skeleton for the AeroVital wearable telemetry client. 

**This component is currently under active development and is NOT YET COMPLETE or verified for operational flight use.**

---

## Planned Architecture

```
Galaxy Watch (Wear OS)
   ├── Samsung Privileged Health SDK (PPG, ECG, SpO2, Accelerometer)
   ├── Local Sensor Sampling & Monotonic Buffering
   └── Bluetooth LE / Wi-Fi Sync
         ↓
Android Companion Phone
   ├── Pilot Authentication (Token Auth)
   ├── Store-and-Forward Offline Cache (Room DB)
   └── HTTPS REST Ingestion Adapter
         ↓
Django REST API (`/api/v1/telemetry/`)
```

---

## Current Implementation State

- [x] Initial Android Studio / Gradle Kotlin DSL build configuration (`build.gradle.kts`, `settings.gradle.kts`)
- [x] Wear OS Compose baseline UI template (`MainActivity.kt`, `Theme.kt`)
- [ ] Samsung Privileged Health SDK integration (real sensor data streams)
- [ ] Bluetooth LE / Wi-Fi telemetry relay to mobile companion
- [ ] Phone gateway application with Django REST API client
- [ ] Offline caching and network retry queue
- [ ] Real-time operational context tagging (G-load, flight phase)

---

## Local Verification Notice

All verified end-to-end demonstrations in the current release use direct synthetic and controlled telemetry ingested via the verified Django REST backend (`POST /api/v1/telemetry/`) and processed by the AeroVital Core Engine. Real wearable hardware streaming is slated for the upcoming integration phase.
