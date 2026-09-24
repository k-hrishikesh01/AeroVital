from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from pilots.models import Pilot
from missions.models import Mission
from intelligence.models import StateEstimate
from .models import Alert


class AlertModelAndAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="safetyofficer", password="password123")
        self.pilot = Pilot.objects.create(
            pilot_code="TEST-PILOT-A1",
            name="Flight Safety Officer",
            age=40,
            sex="F",
        )
        self.mission = Mission.objects.create(
            pilot=self.pilot,
            mission_code="SORTIE-ALERT-01",
            start_time=timezone.now(),
        )
        self.estimate = StateEstimate.objects.create(
            pilot=self.pilot,
            mission=self.mission,
            timestamp=timezone.now(),
            fatigue_state="FATIGUE",
            fatigue_score=0.82,
            confidence=0.85,
            overall_sqi=1.0,
            dominant_factors=["Depressed RMSSD"],
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_alert_query_and_acknowledge(self):
        alert = Alert.objects.create(
            pilot=self.pilot,
            mission=self.mission,
            state_estimate=self.estimate,
            timestamp=timezone.now(),
            alert_type="FATIGUE_WARNING",
            severity=Alert.Severity.WARNING,
            message="Pilot fatigue detected.",
            trigger_state="FATIGUE",
            confidence=0.85,
        )

        # Query unacknowledged alerts
        res = self.client.get(f"/api/v1/alerts/?mission={self.mission.id}&unacknowledged=true")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

        # Acknowledge alert
        ack_res = self.client.post(f"/api/v1/alerts/{alert.id}/acknowledge/")
        self.assertEqual(ack_res.status_code, status.HTTP_200_OK)
        self.assertTrue(ack_res.data["acknowledged"])
        self.assertIsNotNone(ack_res.data["acknowledged_at"])

        # Query unacknowledged again - should be empty
        res_after = self.client.get(f"/api/v1/alerts/?mission={self.mission.id}&unacknowledged=true")
        self.assertEqual(len(res_after.data), 0)
