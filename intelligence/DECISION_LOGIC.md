# AeroVital Intelligence — Decision Logic

## 1. Fundamental Model

AeroVital treats fatigue as a latent operational state inferred from
multiple observations over time.

The engine does not equate any single physiological measurement with
fatigue.

Core inference dimensions:

- physiological evidence
- contextual evidence
- personal baseline deviation
- temporal evidence
- signal quality
- model evidence

---

## 2. Primary Internal Quantities

### Fatigue State

A continuous internal estimate:

F(t) ∈ [0, 1]

representing the strength of evidence supporting fatigue.

### Confidence

C(t) ∈ [0, 1]

representing confidence in the fatigue estimate.

Fatigue magnitude and confidence are independent.

---

## 3. Evidence Channels

### Physiological Evidence

Examples:

- heart rate
- HRV
- respiration
- SpO2
- skin temperature
- EDA

### Contextual Evidence

Examples:

- mission phase
- activity
- task demand
- mission duration
- environmental/contextual information

### Personal Evidence

Current physiology relative to the individual's baseline.

### Temporal Evidence

Information derived from:

- persistence
- trajectory
- accumulation
- recovery
- recent history

---

## 4. Contextual Interpretation

Physiological activation must not automatically be interpreted as fatigue.

The same physiological response may have different interpretations
depending on operational context.

Context may therefore:

- strengthen fatigue interpretation
- weaken fatigue interpretation
- provide an alternative explanation
- leave interpretation unchanged

---

## 5. Signal Quality

Signal quality is evaluated independently of fatigue.

Poor signal quality:

- reduces confidence
- may invalidate specific features
- may trigger sensor-specific fallback behavior

Poor signal quality must not automatically imply fatigue.

---

## 6. Temporal Reasoning

Fatigue inference incorporates recent history.

The engine should distinguish:

- transient physiological changes
- persistent changes
- worsening trajectories
- recovery trajectories

Temporal filtering should prevent unstable state transitions while
remaining responsive to sustained deterioration.

---

## 7. Abstention

The engine may return an insufficient-data / unknown state when:

- signal quality is inadequate
- insufficient history exists
- baseline is unavailable
- required modalities are unavailable
- evidence disagreement is too high

The engine must not fabricate certainty.

---

## 8. Output

The intelligence layer should provide:

- fatigue score
- fatigue state
- confidence
- trend
- signal quality
- dominant evidence
- relevant feature values
- model version

---

## 9. Important Design Principle

AeroVital is an inference engine rather than a single-threshold
fatigue detector.

The architecture separates:

1. observation
2. feature extraction
3. baseline comparison
4. contextual interpretation
5. inference
6. temporal reasoning
7. confidence
8. decision
