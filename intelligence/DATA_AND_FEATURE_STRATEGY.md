# AeroVital Intelligence — Data & Feature Strategy

## 1. Purpose

This document defines which data streams AeroVital Intelligence considers,
how each stream is transformed into information, and what role that
information plays in fatigue inference.

AeroVital does not treat any individual physiological measurement as a
direct measurement of fatigue.

The engine combines physiological evidence, contextual information,
temporal behavior, signal quality, and individual baseline information.

---

# 2. Data Categories

AeroVital divides incoming information into five categories:

1. Physiological signals
2. Motion/activity signals
3. Operational/contextual signals
4. Personal baseline information
5. Signal-quality information

---

# 3. Physiological Signals

## 3.1 Heart Rate

Source:
- ECG
- PPG

Raw information:
- heart rate
- beat-to-beat intervals where available

Derived features:
- mean HR
- median HR
- HR standard deviation
- HR trend
- baseline-relative HR deviation
- rolling HR change

Role:
- physiological evidence
- contextual workload indicator
- baseline deviation

Important:
Elevated HR is not interpreted as fatigue by itself.

Potential alternative explanations include workload, physical activity,
stress, maneuvering, or other physiological activation.

---

## 3.2 RR Intervals

Source:
- ECG / high-quality PPG

Derived features:
- mean RR
- SDNN
- RMSSD
- pNN50
- pNN20
- SD1
- SD2
- LF
- HF
- LF/HF
- normalized LF/HF measures where appropriate

Role:
- autonomic physiological evidence
- fatigue-related feature candidates
- recovery-related feature candidates

Important:
HRV features require an adequate temporal window and signal quality.
They should not be treated as independent instantaneous measurements.

---

## 3.3 Respiration

Potential inputs:
- respiratory rate
- respiratory waveform where available

Derived features:
- mean respiratory rate
- respiratory variability
- respiratory trend
- baseline-relative deviation

Role:
- supporting physiological evidence
- contextual physiological state

---

## 3.4 SpO2

Derived features:
- mean SpO2
- minimum SpO2
- deviation from baseline
- temporal trend

Role:
- supporting physiological/environmental information

SpO2 should not automatically be interpreted as a fatigue measure.

---

## 3.5 Skin Temperature

Derived features:
- mean temperature
- temperature deviation
- temperature trend

Role:
- supporting physiological/contextual feature

---

## 3.6 Electrodermal Activity

Future sensor:
- EDA/GSR

Potential features:
- tonic skin conductance
- phasic response
- response frequency
- response amplitude

Role:
- arousal/contextual physiological information

Status:
Future multimodal extension.

---

# 4. Motion and Activity

Potential sources:
- accelerometer
- gyroscope
- wearable activity sensors

Derived information:
- activity level
- movement intensity
- movement variance
- motion artifact indicators

Role:

1. Context interpretation
2. Artifact detection
3. Differentiating physical activity from low-activity fatigue patterns

Motion must not automatically increase or decrease fatigue.

---

# 5. Operational Context

Potential inputs:

- mission phase
- mission duration
- time since session start
- task type
- workload indicators
- environmental context
- flight events

Role:

Context is used to interpret physiological changes.

Example:

Elevated HR during a high-demand maneuver may have a different
interpretation from persistent elevated HR during low-activity cruise.

Context is therefore an interpretation variable, not a direct fatigue score.

---

# 6. Personal Baseline

The engine should maintain an operator-specific baseline.

Potential baseline variables:

- resting HR
- HRV statistics
- respiration
- SpO2
- temperature
- other validated physiological variables

Baseline-derived features:

- absolute deviation
- relative deviation
- standardized deviation
- rolling deviation
- trend relative to baseline

The system should prefer individual-relative information where
appropriate rather than relying exclusively on population-level thresholds.

---

# 7. Signal Quality

Every physiological stream should have an associated quality assessment.

Potential quality indicators:

- missing samples
- invalid values
- artifact percentage
- continuity
- signal-to-noise characteristics where measurable
- physiological plausibility
- sensor availability
- synchronization quality

Signal quality affects confidence in downstream inference.

Poor signal quality should not automatically be interpreted as fatigue.

---

# 8. Temporal Representation

The engine should process physiological information over time windows
rather than relying exclusively on instantaneous samples.

Candidate window lengths should be experimentally evaluated.

Potential approaches:

- short rolling window
- medium rolling window
- longer contextual window

Window size may differ by feature family.

HRV features require longer windows than instantaneous HR.

---

# 9. Feature Categories

Each feature should be classified as one of:

### Physiological Evidence
Information directly describing physiological state.

### Context
Information describing what the operator is doing or experiencing.

### Baseline Deviation
Information describing how current physiology differs from the
individual's normal state.

### Temporal Evidence
Information describing persistence, trajectory, accumulation, or recovery.

### Signal Quality
Information describing how trustworthy the measurement is.

---

# 10. Fatigue Inference Principle

AeroVital should estimate fatigue using multiple evidence sources.

Conceptually:

Physiological Evidence
+
Baseline Deviation
+
Context
+
Temporal Behavior
+
Signal Quality
+
Model Evidence

→ Fatigue Inference

No single sensor should independently determine fatigue state.

---

# 11. Output

The intelligence layer should provide:

- fatigue score
- fatigue state
- confidence
- trend
- signal quality
- dominant evidence
- relevant features
- model version

---

# 12. Future Extensions

Potential future modalities:

- EEG
- eye tracking
- EMG
- additional contextual/task data
- environmental measurements

These should be added only when their contribution can be justified
through evidence or experimentation.

