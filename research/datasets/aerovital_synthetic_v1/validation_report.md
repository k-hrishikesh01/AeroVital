# AeroVital Synthetic Dataset — Validation Report

**Audit Status:** `ALL 9 AUDITS PASSED (100%)`  
**Validation Timestamp:** `2026-11-25T13:41:27.941584+00:00`  
**Validated Artifacts:** `synthetic_physiological_dataset.csv`, `synthetic_physiological_dataset.jsonl`, `synthetic_physiological_dataset.json`, `participants.json`, `sessions.json`  

## Automated Audit Checklist

| # | Validation Check | Target Metric | Observed Metric | Result |
| :--- | :--- | :--- | :--- | :---: |
| 1 | Participant Uniqueness | 30 unique IDs | 30 unique IDs | **PASSED** |
| 2 | Session Uniqueness | 60 unique IDs | 60 unique IDs | **PASSED** |
| 3 | Total Observations | Exactly 216,000 | 216,000 | **PASSED** |
| 4 | Sampling Continuity | Strictly 1.0s step (1 Hz) | Zero delta deviations | **PASSED** |
| 5 | Physiological HR Range | 40.0 – 190.0 BPM | 47.2 – 126.4 BPM | **PASSED** |
| 6 | Physiological RR Range | 300.0 – 1500.0 ms | 460.8 – 1271.7 ms | **PASSED** |
| 7 | HR / IBI Concordance | Max error < 1.0 BPM | Max: 0.050 BPM, Mean: 0.0250 BPM | **PASSED** |
| 8 | Hardware Non-Fabrication | SpO2/SkinTemp null (zero zeros) | 100% null, 0 zeros | **PASSED** |
| 9 | Operational DB Isolation | 0 synthetic records in prod DB | 0 records written | **PASSED** |
