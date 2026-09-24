from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from pilots.models import Pilot
from .models import Device


class DeviceModelAndAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testoperator", password="password123")
        self.pilot = Pilot.objects.create(
            pilot_code="TEST-PILOT-D1",
            name="Test Pilot",
            age=30,
            sex="F",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_device_registration_and_query(self):
        post_data = {
            "pilot": str(self.pilot.id),
            "device_uid": "GALAXY-WATCH-ULTRA-001",
            "device_type": "WEAR_OS",
            "manufacturer": "Samsung",
            "model": "Galaxy Watch Ultra",
            "firmware_version": "5.0.1",
            "connection_type": "BLE",
            "sampling_rate": 1.0,
            "is_active": True,
        }
        res = self.client.post("/api/v1/devices/", post_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        device_id = res.data["id"]

        res_get = self.client.get(f"/api/v1/devices/{device_id}/")
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data["device_uid"], "GALAXY-WATCH-ULTRA-001")

    def test_duplicate_device_uid_rejected(self):
        Device.objects.create(
            pilot=self.pilot,
            device_uid="DUP-UID-123",
            device_type="WEARABLE",
        )
        res = self.client.post("/api/v1/devices/", {
            "device_uid": "DUP-UID-123",
            "device_type": "WEARABLE",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
