from datetime import datetime, timezone as dt_timezone
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from pilots.models import Pilot
from missions.models import Mission
from .models import Baseline, StateEstimate, ModelVersion
from backend.core.schemas.baseline import PilotBaseline
from backend.core.schemas.result import FatigueEstimationResult, FatigueState, EstimationMetadata


class IntelligenceModelAndAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="intelanalyst", password="password123")
        self.pilot = Pilot.objects.create(
            pilot_code="PILOT-INTEL-01",
            name="Major John Doe",
            age=36,
            sex="M",
        )
        self.mission = Mission.objects.create(
            pilot=self.pilot,
            mission_code="INTEL-SORTIE-01",
            start_time=timezone.now(),
            status="ACTIVE",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_baseline_core_roundtrip(self):
        now = datetime.now(dt_timezone.utc)
        baseline = Baseline.objects.create(
            pilot=self.pilot,
            baseline_version="BASELINE-2026-v1",
            resting_heart_rate=62.0,
            baseline_rmssd=45.5,
            baseline_sdnn=55.0,
            baseline_mean_rr=967.0,
            calibration_duration_sec=300.0,
            is_calibrated=True,
            metadata={"ambient_temp_c": 22.0},
            created_at=now,
        )

        core_bl = baseline.to_core()
        self.assertIsInstance(core_bl, PilotBaseline)
        self.assertEqual(core_bl.pilot_id, str(self.pilot.id))
        self.assertEqual(core_bl.resting_heart_rate, 62.0)
        self.assertEqual(core_bl.baseline_rmssd, 45.5)
        self.assertTrue(core_bl.is_calibrated)

    def test_insufficient_data_with_none_fatigue_score_persists_successfully(self):
        """CRITICAL: INSUFFICIENT_DATA with fatigue_score=None must NOT cause IntegrityError."""
        now = datetime.now(dt_timezone.utc)
        core_result = FatigueEstimationResult(
            timestamp=now,
            fatigue_score=None,  # Explicitly None
            fatigue_state=FatigueState.INSUFFICIENT_DATA,
            confidence=0.25,
            dominant_factors=["Physiological sensor channels unreliable or motion-corrupted"],
            overall_sqi=0.45,
            metadata=EstimationMetadata(
                estimator_id="ProvisionalRuleBasedEstimator",
                is_provisional=True,
                disclaimer="Provisional test",
                confidence_threshold_used=0.40,
                baseline_version_used=None,
            ),
        )

        estimate = StateEstimate.from_core(
            result=core_result,
            pilot=self.pilot,
            mission=self.mission,
        )

        self.assertIsNotNone(estimate.id)
        self.assertEqual(estimate.fatigue_state, "INSUFFICIENT_DATA")
        self.assertIsNone(estimate.fatigue_score)
        self.assertEqual(estimate.confidence, 0.25)
        self.assertEqual(estimate.overall_sqi, 0.45)
        self.assertEqual(estimate.dominant_factors, ["Physiological sensor channels unreliable or motion-corrupted"])

    def test_all_four_valid_core_states_can_be_stored(self):
        """Verify NORMAL, ELEVATED_WORKLOAD, FATIGUE, and INSUFFICIENT_DATA states."""
        now = datetime.now(dt_timezone.utc)
        states = [
            (FatigueState.NORMAL, 0.15, 0.95),
            (FatigueState.ELEVATED_WORKLOAD, 0.45, 0.90),
            (FatigueState.FATIGUE, 0.85, 0.92),
            (FatigueState.INSUFFICIENT_DATA, None, 0.30),
        ]

        for core_state, score, conf in states:
            res = FatigueEstimationResult(
                timestamp=now,
                fatigue_score=score,
                fatigue_state=core_state,
                confidence=conf,
                dominant_factors=[f"Test factor for {core_state.value}"],
                overall_sqi=1.0 if score is not None else 0.5,
                metadata=EstimationMetadata(
                    estimator_id="ProvisionalRuleBasedEstimator",
                    baseline_version_used="BASELINE-v1",
                ),
            )
            est = StateEstimate.from_core(
                result=res,
                pilot=self.pilot,
                mission=self.mission,
            )
            self.assertEqual(est.fatigue_state, core_state.value)
            self.assertEqual(est.fatigue_score, score)
            self.assertEqual(est.confidence, conf)

    def test_dashboard_current_state_endpoint(self):
        now = datetime.now(dt_timezone.utc)
        res = FatigueEstimationResult(
            timestamp=now,
            fatigue_score=0.78,
            fatigue_state=FatigueState.FATIGUE,
            confidence=0.88,
            dominant_factors=["Depressed HRV RMSSD", "Benign flight phase"],
            overall_sqi=0.98,
            metadata=EstimationMetadata(
                estimator_id="ProvisionalRuleBasedEstimator",
                baseline_version_used="BASELINE-2026-Q3",
            ),
        )
        StateEstimate.from_core(
            result=res,
            pilot=self.pilot,
            mission=self.mission,
            evidence={"hr_deviation": 1.0, "rmssd_ratio": 0.16},
        )

        response = self.client.get(f"/api/v1/intelligence/current-state/?mission={self.mission.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_state"], "FATIGUE")
        self.assertEqual(response.data["fatigue_score"], 0.78)
        self.assertEqual(response.data["confidence"], 0.88)
        self.assertEqual(response.data["overall_sqi"], 0.98)
        self.assertIn("Depressed HRV RMSSD", response.data["dominant_factors"])
        self.assertEqual(response.data["baseline_version"], "BASELINE-2026-Q3")
