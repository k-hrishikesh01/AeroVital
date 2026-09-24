from datetime import datetime, timedelta, timezone as dt_timezone
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from pilots.models import Pilot
from devices.models import Device
from missions.models import Mission
from intelligence.models import Baseline, StateEstimate
from alerts.models import Alert
from .models import Telemetry, SignalQuality, FeatureWindow
from .services import pipeline_manager


class TelemetryCoreIntegrationTestCase(TestCase):
    def setUp(self):
        # Reset session manager cache between tests
        pipeline_manager._cache.clear()

        self.user = User.objects.create_user(username="telemetryoperator", password="password123")
        self.pilot = Pilot.objects.create(
            pilot_code="TEST-PILOT-T1",
            name="Lt. Tom Kazansky",
            age=31,
            sex="M",
            is_active=True,
        )
        self.device = Device.objects.create(
            pilot=self.pilot,
            device_uid="WATCH-TEST-001",
            device_type="WEAR_OS",
            manufacturer="AeroVital",
            model="ProSensor",
            is_active=True,
        )
        self.mission = Mission.objects.create(
            pilot=self.pilot,
            mission_code="MISSION-TEST-01",
            current_phase="CRUISE",
            external_g_load=1.0,
            start_time=timezone.now(),
            status="ACTIVE",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = "/api/v1/telemetry/"

    def test_valid_telemetry_stored_and_raw_payload_preserved(self):
        data = {
            "pilot": str(self.pilot.id),
            "device": str(self.device.id),
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:00:00Z",
            "heart_rate": 72.0,
            "rr_interval": 833.3,
            "spo2": 98.0,
            "skin_temperature": 36.2,
            "activity_level": 0.2,
            "steps": 150,
            "accel_x": 0.05,
            "accel_y": 0.10,
            "accel_z": 0.98,
            "battery_level": 94.0,
            "raw_payload": {"device_vendor": "WearOS", "sensor_id": "ppg_01"},
        }
        res = self.client.post(self.url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Telemetry.objects.count(), 1)

        record = Telemetry.objects.first()
        self.assertEqual(record.heart_rate, 72.0)
        self.assertEqual(record.raw_payload["sensor_id"], "ppg_01")
        self.assertEqual(res.data["status"], "accumulating")

    def test_invalid_heart_rate_rejected_by_core_validator(self):
        """Heart rate below physiological limits (30 BPM) or above (240 BPM) must be rejected."""
        data_low = {
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:01:00Z",
            "heart_rate": 15.0,  # Below 30 BPM physiological floor
        }
        res_low = self.client.post(self.url, data_low, format="json")
        self.assertEqual(res_low.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("telemetry_validation_error", res_low.data)

        data_high = {
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:01:00Z",
            "heart_rate": 260.0,  # Above 240 BPM physiological ceiling
        }
        res_high = self.client.post(self.url, data_high, format="json")
        self.assertEqual(res_high.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_spo2_rejected_by_core_validator(self):
        data = {
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:02:00Z",
            "spo2": 105.0,  # Above 100%
        }
        res = self.client.post(self.url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_skin_temperature_rejected_by_core_validator(self):
        data = {
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:03:00Z",
            "skin_temperature": 52.0,  # Implausible physiological skin temp
        }
        res = self.client.post(self.url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_incomplete_accelerometer_triplet_rejected(self):
        """Incomplete 3-axis accelerometer triplet violates Core structure."""
        data = {
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:04:00Z",
            "accel_x": 0.5,
            # accel_y and accel_z omitted!
        }
        res = self.client.post(self.url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_optional_channels_can_be_omitted_without_fabrication(self):
        data = {
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:05:00Z",
            "heart_rate": 70.0,
        }
        res = self.client.post(self.url, data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        record = Telemetry.objects.first()
        self.assertIsNone(record.rr_interval)
        self.assertIsNone(record.spo2)
        self.assertIsNone(record.skin_temperature)
        self.assertIsNone(record.accel_x)

    def test_rr_interval_accepts_scalar_and_list_of_floats(self):
        # Scalar
        res1 = self.client.post(self.url, {
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:06:00Z",
            "rr_interval": 800.0,
        }, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Telemetry.objects.get(timestamp="2026-09-24T10:06:00Z").rr_interval, 800.0)

        # List of floats
        res2 = self.client.post(self.url, {
            "mission": str(self.mission.id),
            "timestamp": "2026-09-24T10:07:00Z",
            "rr_interval": [800.0, 810.5, 795.2],
        }, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Telemetry.objects.get(timestamp="2026-09-24T10:07:00Z").rr_interval,
            [800.0, 810.5, 795.2],
        )

    def test_streaming_window_accumulation_and_evaluation(self):
        """Verify window buffer progression: samples 1-4 accumulate; sample 5 triggers Core evaluation."""
        base_time = datetime(2026, 9, 24, 12, 0, 0, tzinfo=dt_timezone.utc)

        # Add pilot baseline to enable full evaluation
        Baseline.objects.create(
            pilot=self.pilot,
            baseline_version="BASELINE-2026-v1",
            resting_heart_rate=65.0,
            baseline_rmssd=48.0,
            baseline_sdnn=50.0,
            baseline_mean_rr=923.0,
            is_calibrated=True,
        )

        # Ingest first 4 samples (under minimum window threshold of 5)
        for i in range(4):
            t = base_time + timedelta(seconds=i * 2)
            res = self.client.post(self.url, {
                "mission": str(self.mission.id),
                "pilot": str(self.pilot.id),
                "timestamp": t.isoformat(),
                "heart_rate": 66.0,
                "rr_interval": [900.0, 910.0],
            }, format="json")
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            self.assertEqual(res.data["status"], "accumulating")
            self.assertIsNone(res.data["estimate"])

        # Ingest 5th sample (reaches minimum window threshold)
        t5 = base_time + timedelta(seconds=8)
        res5 = self.client.post(self.url, {
            "mission": str(self.mission.id),
            "pilot": str(self.pilot.id),
            "timestamp": t5.isoformat(),
            "heart_rate": 66.0,
            "rr_interval": [900.0, 910.0],
        }, format="json")

        self.assertEqual(res5.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res5.data["status"], "evaluated")
        self.assertIsNotNone(res5.data["estimate"])
        self.assertIn("fatigue_state", res5.data["estimate"])
        self.assertIn("confidence", res5.data["estimate"])

        # Check DB persistence
        self.assertEqual(StateEstimate.objects.count(), 1)
        self.assertEqual(SignalQuality.objects.count(), 1)
        self.assertEqual(FeatureWindow.objects.count(), 1)

    def test_controlled_fatigue_scenario_produces_fatigue_and_alert(self):
        """End-to-End: Depressed beat-to-beat variability in benign cruise context triggers FATIGUE and Alert."""
        base_time = datetime(2026, 9, 24, 14, 0, 0, tzinfo=dt_timezone.utc)

        # Baseline: resting HR 60, RMSSD 50.0 ms
        Baseline.objects.create(
            pilot=self.pilot,
            baseline_version="BASELINE-CALIBRATED-Q3",
            resting_heart_rate=60.0,
            baseline_rmssd=50.0,
            baseline_sdnn=55.0,
            baseline_mean_rr=1000.0,
            is_calibrated=True,
        )

        # Ingest 5 samples with depressed RMSSD (~8ms vs baseline 50ms, ratio < 0.20) in CRUISE phase
        latest_res = None
        for i in range(5):
            t = base_time + timedelta(seconds=i * 2)
            latest_res = self.client.post(self.url, {
                "mission": str(self.mission.id),
                "pilot": str(self.pilot.id),
                "timestamp": t.isoformat(),
                "heart_rate": 61.0,  # Nominal HR
                # Depressed successive differences: alternating +/- 8ms
                "rr_interval": [980.0, 988.0, 980.0, 988.0],
            }, format="json")

        self.assertEqual(latest_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(latest_res.data["status"], "evaluated")

        est = StateEstimate.objects.first()
        self.assertIsNotNone(est)
        self.assertEqual(est.fatigue_state, "FATIGUE")
        self.assertGreaterEqual(est.confidence, 0.70)
        # Per verified Core specification (Option B): fatigue_score is strictly None
        self.assertIsNone(est.fatigue_score)

        # Verify Alert generation
        alert = Alert.objects.filter(state_estimate=est).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, "FATIGUE_WARNING")
        self.assertEqual(alert.severity, Alert.Severity.WARNING)

    def test_batch_window_evaluation_endpoint(self):
        base_time = datetime(2026, 9, 24, 16, 0, 0, tzinfo=dt_timezone.utc)
        samples = []
        for i in range(5):
            t = base_time + timedelta(seconds=i * 2)
            samples.append({
                "timestamp": t.isoformat(),
                "heart_rate": 68.0,
                "rr_interval": [880.0, 885.0],
            })

        res = self.client.post("/api/v1/telemetry/batch/", {
            "mission": str(self.mission.id),
            "pilot": str(self.pilot.id),
            "samples": samples,
        }, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["status"], "evaluated")
        self.assertEqual(res.data["telemetry_count"], 5)
        self.assertIsNotNone(res.data["estimate"])

    def test_controlled_workload_scenario_produces_elevated_workload(self):
        """End-to-End: High G-load and Combat Maneuver with high HR produces ELEVATED_WORKLOAD."""
        # Update mission to high workload context
        self.mission.current_phase = "COMBAT_MANEUVER"
        self.mission.external_g_load = 3.5
        self.mission.save()

        Baseline.objects.create(
            pilot=self.pilot,
            baseline_version="BASELINE-WORKLOAD-TEST",
            resting_heart_rate=65.0,
            baseline_rmssd=50.0,
            is_calibrated=True,
        )

        base_time = datetime(2026, 9, 24, 17, 0, 0, tzinfo=dt_timezone.utc)
        latest_res = None
        for i in range(5):
            t = base_time + timedelta(seconds=i * 2)
            latest_res = self.client.post(self.url, {
                "mission": str(self.mission.id),
                "pilot": str(self.pilot.id),
                "timestamp": t.isoformat(),
                "heart_rate": 90.0,  # Elevated HR (+25 relative to 65 baseline)
                "rr_interval": [630.0, 635.0, 630.0, 635.0],
            }, format="json")

        self.assertEqual(latest_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(latest_res.data["status"], "evaluated")

        est = StateEstimate.objects.filter(mission=self.mission).first()
        self.assertIsNotNone(est)
        self.assertEqual(est.fatigue_state, "ELEVATED_WORKLOAD")
        self.assertGreaterEqual(est.confidence, 0.70)

    def test_controlled_normal_scenario_produces_normal(self):
        """End-to-End: Nominal HR and HRV within baseline limits produces NORMAL state."""
        self.mission.current_phase = "CRUISE"
        self.mission.external_g_load = 1.0
        self.mission.save()

        Baseline.objects.create(
            pilot=self.pilot,
            baseline_version="BASELINE-NORMAL-TEST",
            resting_heart_rate=68.0,
            baseline_rmssd=45.0,
            is_calibrated=True,
        )

        base_time = datetime(2026, 9, 24, 18, 0, 0, tzinfo=dt_timezone.utc)
        latest_res = None
        for i in range(5):
            t = base_time + timedelta(seconds=i * 2)
            latest_res = self.client.post(self.url, {
                "mission": str(self.mission.id),
                "pilot": str(self.pilot.id),
                "timestamp": t.isoformat(),
                "heart_rate": 69.0,  # Concordant HR
                "rr_interval": [870.0, 915.0, 870.0, 915.0],  # RMSSD ~45ms concordant
            }, format="json")

        self.assertEqual(latest_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(latest_res.data["status"], "evaluated")

        est = StateEstimate.objects.filter(mission=self.mission).first()
        self.assertIsNotNone(est)
        self.assertEqual(est.fatigue_state, "NORMAL")
        self.assertGreaterEqual(est.confidence, 0.80)

    def test_controlled_missing_rr_produces_insufficient_data(self):
        """End-to-End: When essential autonomic RR channel is absent, Core abstains with INSUFFICIENT_DATA."""
        base_time = datetime(2026, 9, 24, 19, 0, 0, tzinfo=dt_timezone.utc)
        latest_res = None
        for i in range(5):
            t = base_time + timedelta(seconds=i * 2)
            latest_res = self.client.post(self.url, {
                "mission": str(self.mission.id),
                "pilot": str(self.pilot.id),
                "timestamp": t.isoformat(),
                "heart_rate": 70.0,
                # rr_interval omitted entirely
            }, format="json")

        self.assertEqual(latest_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(latest_res.data["status"], "evaluated")

        est = StateEstimate.objects.filter(mission=self.mission).first()
        self.assertIsNotNone(est)
        self.assertEqual(est.fatigue_state, "INSUFFICIENT_DATA")
        self.assertIsNone(est.fatigue_score)

    def test_telemetry_history_query(self):
        now = timezone.now()
        Telemetry.objects.create(
            mission=self.mission,
            pilot=self.pilot,
            device=self.device,
            timestamp=now,
            heart_rate=72.0,
        )
        res = self.client.get(f"/api/v1/telemetry/?mission={self.mission.id}")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

