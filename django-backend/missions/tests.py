from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from pilots.models import Pilot
from .models import Mission
from alerts.models import MissionEvent


class MissionModelAndAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="missionadmin", password="password123")
        self.pilot = Pilot.objects.create(
            pilot_code="TEST-PILOT-M1",
            name="Flight Lead",
            age=32,
            sex="M",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_mission_lifecycle_and_completion(self):
        start = timezone.now()
        res = self.client.post("/api/v1/missions/", {
            "pilot": str(self.pilot.id),
            "mission_code": "SORTIE-ALPHA-99",
            "mission_type": "HIGH_ALTITUDE_RECON",
            "current_phase": "CLIMB",
            "external_g_load": 1.5,
            "start_time": start.isoformat(),
            "status": "ACTIVE",
            "environment": {"weather": "clear", "temp_c": 18.0},
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        mission_id = res.data["id"]

        # Add event to mission
        event_res = self.client.post(f"/api/v1/missions/{mission_id}/events/", {
            "timestamp": timezone.now().isoformat(),
            "event_type": "AIRSPACE_ENTRY",
            "event_value": {"sector": "B-4"},
            "description": "Entered operational area",
        }, format="json")
        self.assertEqual(event_res.status_code, status.HTTP_201_CREATED)

        # Complete mission
        comp_res = self.client.post(f"/api/v1/missions/{mission_id}/complete/")
        self.assertEqual(comp_res.status_code, status.HTTP_200_OK)
        self.assertEqual(comp_res.data["status"], "COMPLETED")
        self.assertIsNotNone(comp_res.data["end_time"])
