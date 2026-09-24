from django.test import TestCase
from rest_framework.test import APIClient
from pilots.models import Pilot
from missions.models import Mission
from devices.models import Device
from .models import Telemetry


class TelemetryAPITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.pilot = Pilot.objects.create(
            pilot_code="TEST-PILOT",
            name="Test Pilot",
            age=30,
            sex="M",
            is_active=True
        )

        self.mission = Mission.objects.create(
            pilot=self.pilot,
            mission_code="TEST-MISSION",
            mission_type="TEST",
            start_time="2026-09-24T10:00:00Z",
            status="PLANNED",
            environment={}
        )

        self.device = Device.objects.create(pilot=self.pilot,
            device_uid="TEST-DEVICE",
            device_type="WEARABLE",
            manufacturer="AeroVital",
            model="Test Sensor",
            firmware_version="1.0",
            connection_type="BLE",
            sampling_rate=1.0,
            is_active=True
        )

        self.url = "/api/"

    def test_valid_telemetry_is_accepted_and_stored(self):
        data = {
            "mission": str(self.mission.id),
            "device": str(self.device.id),
            "timestamp": "2026-09-24T10:00:00Z",
            "heart_rate": 75.0,
            "rr_interval": 0.8,
            "spo2": 98.0,
            "skin_temperature": 36.5,
            "activity_level": 0.5,
            "steps": 100,
            "accel_x": 0.1,
            "accel_y": 0.2,
            "accel_z": 0.3,
            "battery_level": 95.0,
            "raw_payload": {"source": "automated-test"}
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Telemetry.objects.count(), 1)

    def test_negative_heart_rate_is_rejected_and_not_stored(self):
        data = {
            "mission": str(self.mission.id),
            "device": str(self.device.id),
            "timestamp": "2026-09-24T10:05:00Z",
            "heart_rate": -10.0,
            "raw_payload": {"source": "invalid-test"}
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Telemetry.objects.count(), 0)

    def test_optional_channels_can_be_omitted(self):
        data = {
            "mission": str(self.mission.id),
            "device": str(self.device.id),
            "timestamp": "2026-09-24T10:10:00Z",
            "raw_payload": {"source": "optional-channel-test"}
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, 201)

        telemetry = Telemetry.objects.get()

        self.assertIsNone(telemetry.heart_rate)
        self.assertIsNone(telemetry.rr_interval)
        self.assertIsNone(telemetry.spo2)
        self.assertIsNone(telemetry.skin_temperature)
