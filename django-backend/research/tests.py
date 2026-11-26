"""Unit and Integration Tests for AeroVital Research App.

Exhaustively verifies:
1. Authentication & Authorization across all endpoints.
2. Dataset Manifest and Metadata retrieval.
3. Scenario filtering and participant baseline access.
4. Selective timeseries streaming and downsampling integrity.
5. Path traversal security and malformed ID validation.
6. Real AeroVitalPipeline execution bridging without algorithmic mutation.
7. Run persistence and per-window result retrieval.
8. Multi-run comparison functionality and version divergence detection.
9. Data export in CSV and JSON formats.
10. Strict operational data isolation (0 writes to operational telemetry/missions/alerts).
"""

import importlib
import os
from datetime import datetime, timezone
from django.apps import apps as django_apps
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from alerts.models import Alert
from missions.models import Mission
from pilots.models import Pilot
from research.models import ResearchRun
from research.services import EngineExecutionService
from telemetry.models import Telemetry


class ResearchAppTests(TestCase):
    """Test suite for AeroVital Research Lab backend API."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="researcher",
            password="ResearchPassword123!",
        )
        self.pilot = Pilot.objects.create(
            user=self.user,
            pilot_code="RS-001",
            name="Dr. Research Director",
        )
        # Authenticate
        self.client.force_authenticate(user=self.user)

    def test_01_authentication_enforcement(self):
        """Unauthenticated requests must be rejected with 401 across endpoints."""
        unauthenticated_client = APIClient()
        endpoints = [
            "/api/v1/research/manifest/",
            "/api/v1/research/participants/",
            "/api/v1/research/sessions/",
            "/api/v1/research/sessions/SYN-S001/timeseries/",
            "/api/v1/research/runs/",
            "/api/v1/research/export/SYN-S001/",
        ]
        for url in endpoints:
            res = unauthenticated_client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {url} did not enforce authentication.",
            )

        post_res = unauthenticated_client.post("/api/v1/research/execute/", {"session_id": "SYN-S001"})
        self.assertEqual(post_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_02_manifest_retrieval(self):
        """Manifest returns complete metadata, provenance, and isolation statement."""
        res = self.client.get("/api/v1/research/manifest/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["dataset_id"], "aerovital-synthetic-v1")
        self.assertEqual(res.data["total_participants"], 30)
        self.assertEqual(res.data["total_sessions"], 60)
        self.assertEqual(res.data["total_records"], 216000)
        self.assertEqual(res.data["random_seed"], 42)
        self.assertIn("operational_isolation_statement", res.data)

    def test_03_participants_listing(self):
        """Participants endpoint returns 30 synthetic profiles with baseline metrics."""
        res = self.client.get("/api/v1/research/participants/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 30)
        first_p = res.data[0]
        self.assertEqual(first_p["pilot_id"], "SYN-P001")
        self.assertIn("resting_heart_rate", first_p)
        self.assertIn("baseline_rmssd", first_p)
        self.assertIn("baseline_mean_rr", first_p)
        self.assertTrue(first_p["is_calibrated"])

    def test_04_sessions_listing_and_filtering(self):
        """Sessions endpoint supports scenario filtering and returns empirical stats."""
        # Unfiltered -> 60 sessions
        res_all = self.client.get("/api/v1/research/sessions/")
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_all.data), 60)

        # Filter: NORMAL_BASELINE -> 12 sessions
        res_norm = self.client.get("/api/v1/research/sessions/?scenario=NORMAL_BASELINE")
        self.assertEqual(res_norm.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_norm.data), 12)
        for s in res_norm.data:
            self.assertEqual(s["scenario"], "NORMAL_BASELINE")
            self.assertEqual(s["duration_sec"], 3600)

        # Filter: FATIGUE_PHYSIOLOGICAL -> 12 sessions
        res_fatigue = self.client.get("/api/v1/research/sessions/?scenario=FATIGUE_PHYSIOLOGICAL")
        self.assertEqual(res_fatigue.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_fatigue.data), 12)

    def test_05_path_traversal_and_malformed_ids(self):
        """Malformed session/participant identifiers and path traversal attempts must fail."""
        invalid_sessions = [
            "../../etc/passwd",
            "SYN-S9999",
            "SYN_S001",
            "SYN-S00",
            "drop table",
            "SYN-S999",  # Valid format, non-existent session
        ]
        for inv in invalid_sessions:
            res = self.client.get(f"/api/v1/research/sessions/{inv}/timeseries/")
            self.assertIn(
                res.status_code,
                [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND],
                f"Expected error for '{inv}', got {res.status_code}",
            )

        # Malformed execution request
        post_bad = self.client.post("/api/v1/research/execute/", {"session_id": "SYN-S9999"})
        self.assertEqual(post_bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_06_timeseries_streaming_and_downsampling(self):
        """Timeseries endpoint selectively streams records and downsamples accurately."""
        # Full (downsample=1) -> 3,600 points
        res_full = self.client.get("/api/v1/research/sessions/SYN-S001/timeseries/?downsample=1")
        self.assertEqual(res_full.status_code, status.HTTP_200_OK)
        self.assertEqual(res_full.data["total_points"], 3600)

        # Downsample factor 5 -> ~721 points
        res_ds5 = self.client.get("/api/v1/research/sessions/SYN-S001/timeseries/?downsample=5")
        self.assertEqual(res_ds5.status_code, status.HTTP_200_OK)
        self.assertEqual(res_ds5.data["total_points"], 721)

        # Verify hardware non-fabrication: SpO2 and skin_temp are None (JSON null)
        first_point = res_ds5.data["data"][0]
        self.assertIsNone(first_point["spo2"])
        self.assertIsNone(first_point["skin_temperature"])
        self.assertIsNotNone(first_point["heart_rate"])
        self.assertIsNotNone(first_point["external_g_load"])

    def test_07_engine_execution_and_run_persistence(self):
        """POST /api/v1/research/execute/ runs the real AeroVitalPipeline and persists results."""
        post_res = self.client.post("/api/v1/research/execute/", {
            "session_id": "SYN-S001",
            "notes": "Automated verification test run",
        })
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)
        data = post_res.data

        # Check returned fields
        run_id = data["run_id"]
        self.assertTrue(run_id.startswith("RUN-"))
        self.assertEqual(data["session_id"], "SYN-S001")
        self.assertEqual(data["scenario"], "NORMAL_BASELINE")
        self.assertEqual(data["total_samples_processed"], 3600)
        self.assertEqual(data["total_windows_evaluated"], 3596)  # 3600 - (60 - 5 + 1) window buildup
        self.assertGreater(data["throughput_samples_per_sec"], 500.0)
        self.assertIn("NORMAL", data["state_breakdown"])
        self.assertGreater(data["state_breakdown"]["NORMAL"]["percentage"], 90.0)

        # Verify persistence in database
        db_run = ResearchRun.objects.get(run_id=run_id)
        self.assertEqual(db_run.session_id, "SYN-S001")
        self.assertEqual(db_run.notes, "Automated verification test run")
        self.assertEqual(db_run.created_by, self.user)
        self.assertEqual(len(db_run.window_outputs), 3596)

    def test_08_run_list_and_detail(self):
        """Historical runs can be listed and retrieved in full detail."""
        # Create two runs
        run1 = EngineExecutionService.execute_session(session_id="SYN-S001", user=self.user)
        run2 = EngineExecutionService.execute_session(session_id="SYN-S013", user=self.user)

        # List runs
        res_list = self.client.get("/api/v1/research/runs/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_list.data), 2)

        # Filter list by session
        res_filt = self.client.get("/api/v1/research/runs/?session=SYN-S013")
        self.assertEqual(res_filt.status_code, status.HTTP_200_OK)
        self.assertTrue(all(r["session_id"] == "SYN-S013" for r in res_filt.data))

        # Retrieve detail
        res_detail = self.client.get(f"/api/v1/research/runs/{run2['run_id']}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["run_id"], run2["run_id"])
        self.assertEqual(res_detail.data["scenario"], "ELEVATED_COGNITIVE_WORKLOAD")
        self.assertIn("ELEVATED_WORKLOAD", res_detail.data["state_breakdown"])

    def test_09_run_comparison(self):
        """Runs can be compared side-by-side with difference flags."""
        run1 = EngineExecutionService.execute_session(session_id="SYN-S001", user=self.user)
        run2 = EngineExecutionService.execute_session(session_id="SYN-S025", user=self.user)

        # Valid comparison
        url = f"/api/v1/research/runs/compare/?run_ids={run1['run_id']},{run2['run_id']}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["compared_run_count"], 2)
        self.assertTrue(res.data["version_differences"]["scenario_diff"])

        # Invalid comparison (single ID)
        bad_url = f"/api/v1/research/runs/compare/?run_ids={run1['run_id']}"
        res_bad = self.client.get(bad_url)
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_10_export_csv_and_json(self):
        """Export endpoint streams valid CSV and JSON with classification metadata."""
        # Export as CSV
        res_csv = self.client.get("/api/v1/research/export/SYN-S001/?format=csv")
        self.assertEqual(res_csv.status_code, status.HTTP_200_OK)
        self.assertEqual(res_csv["Content-Type"], "text/csv")
        content_csv = res_csv.content.decode("utf-8")
        self.assertIn("timestamp,participant_id,session_id", content_csv)
        self.assertIn("SYN-S001", content_csv)

        # Export as JSON
        res_json = self.client.get("/api/v1/research/export/SYN-S001/?format=json")
        self.assertEqual(res_json.status_code, status.HTTP_200_OK)
        self.assertEqual(res_json["Content-Type"], "application/json")
        content_json = res_json.json()
        self.assertEqual(content_json["session_id"], "SYN-S001")
        self.assertEqual(content_json["total_observations"], 3600)

    def test_11_strict_operational_data_isolation(self):
        """Research execution must NEVER write to operational tables."""
        # Record pre-execution row counts
        initial_telemetry_count = Telemetry.objects.count()
        initial_mission_count = Mission.objects.count()
        initial_alert_count = Alert.objects.count()
        initial_pilot_count = Pilot.objects.count()

        # Execute research pipeline
        post_res = self.client.post("/api/v1/research/execute/", {"session_id": "SYN-S049"})
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)

        # Verify operational row counts are strictly unchanged
        self.assertEqual(Telemetry.objects.count(), initial_telemetry_count)
        self.assertEqual(Mission.objects.count(), initial_mission_count)
        self.assertEqual(Alert.objects.count(), initial_alert_count)
        self.assertEqual(Pilot.objects.count(), initial_pilot_count)

        # Confirm research table alone received the record
        self.assertEqual(ResearchRun.objects.filter(session_id="SYN-S049").count(), 1)

    def test_12_duplicate_run_ids_rejected(self):
        """Duplicate run IDs in comparison request must return HTTP 400 Bad Request."""
        run1 = EngineExecutionService.execute_session(session_id="SYN-S001", user=self.user)
        dup_url = f"/api/v1/research/runs/compare/?run_ids={run1['run_id']},{run1['run_id']}"
        res = self.client.get(dup_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("distinct", res.data["detail"].lower())

    def test_13_variable_length_downsampling_and_final_record(self):
        """Downsampling dynamically guarantees preservation of the session terminal observation."""
        from research.services import registry
        records_ds10 = registry.stream_session_records("SYN-S001", downsample_factor=10)
        # Session duration is 3600s, observation 0 to 3599.
        # First point: flight_duration_sec = 0
        # Final point: flight_duration_sec = 3599
        self.assertEqual(records_ds10[0]["flight_duration_sec"], 0)
        self.assertEqual(records_ds10[-1]["flight_duration_sec"], 3599)

    def test_14_unauthenticated_export_rejection_and_token_query_safety(self):
        """Export endpoint strictly rejects unauthenticated requests and rejects token query-params."""
        unauthenticated_client = APIClient()
        # Request without header
        res_no_auth = unauthenticated_client.get("/api/v1/research/export/SYN-S001/?format=csv")
        self.assertEqual(res_no_auth.status_code, status.HTTP_401_UNAUTHORIZED)

        # Request with pseudo-token query param (must not authenticate via query param)
        res_query_token = unauthenticated_client.get("/api/v1/research/export/SYN-S001/?format=csv&token=fake-token-123")
        self.assertEqual(res_query_token.status_code, status.HTTP_401_UNAUTHORIZED)


class DemoResearcherMigrationTests(TestCase):
    """Tests for research migration 0002_create_demo_accounts idempotent behavior."""

    def setUp(self):
        User.objects.filter(username="demo_researcher").delete()
        self.migration_mod = importlib.import_module("research.migrations.0002_create_demo_accounts")
        self.create_func = self.migration_mod.create_demo_researcher
        self.apps = django_apps

    def tearDown(self):
        User.objects.filter(username="demo_researcher").delete()

    def test_existing_account_preserves_password_and_fields(self):
        """Case 1: Existing demo_researcher account credentials and fields must remain unchanged."""
        original_hash = make_password("PreExistingPass999!")
        User.objects.create(
            username="demo_researcher",
            email="existing@aerovital.internal",
            first_name="Existing",
            last_name="User",
            password=original_hash,
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        os.environ["DEMO_RESEARCHER_PASSWORD"] = "DifferentPass123!"
        self.create_func(self.apps, None)
        user = User.objects.get(username="demo_researcher")
        self.assertEqual(user.password, original_hash)
        self.assertTrue(check_password("PreExistingPass999!", user.password))
        self.assertEqual(user.email, "existing@aerovital.internal")
        self.assertEqual(user.first_name, "Existing")

    def test_new_account_created_with_hashed_password(self):
        """Case 2: When account does not exist, it is created with hashed DEMO_RESEARCHER_PASSWORD."""
        User.objects.filter(username="demo_researcher").delete()
        os.environ["DEMO_RESEARCHER_PASSWORD"] = "SecureTestPass2026!"
        self.create_func(self.apps, None)
        user = User.objects.get(username="demo_researcher")
        self.assertTrue(check_password("SecureTestPass2026!", user.password))
        self.assertFalse(check_password("WrongPass", user.password))
        self.assertTrue(user.is_active)

    def test_missing_environment_variable_fails_safely(self):
        """Case 3: When account does not exist and env var is missing, fail safely without creating user."""
        User.objects.filter(username="demo_researcher").delete()
        old_val = os.environ.pop("DEMO_RESEARCHER_PASSWORD", None)
        try:
            with self.assertRaises(ImproperlyConfigured):
                self.create_func(self.apps, None)
            self.assertFalse(User.objects.filter(username="demo_researcher").exists())
        finally:
            if old_val is not None:
                os.environ["DEMO_RESEARCHER_PASSWORD"] = old_val

    def test_repeated_execution_is_idempotent(self):
        """Case 4: Repeated execution does not duplicate accounts or overwrite credentials."""
        User.objects.filter(username="demo_researcher").delete()
        os.environ["DEMO_RESEARCHER_PASSWORD"] = "Run1Password!"
        self.create_func(self.apps, None)
        user1 = User.objects.get(username="demo_researcher")
        first_hash = user1.password

        # Second run with different env var
        os.environ["DEMO_RESEARCHER_PASSWORD"] = "Run2Password!"
        self.create_func(self.apps, None)
        self.assertEqual(User.objects.filter(username="demo_researcher").count(), 1)
        user2 = User.objects.get(username="demo_researcher")
        self.assertEqual(user2.password, first_hash)

    def test_staff_and_superuser_privileges_are_not_granted(self):
        """Case 5: Newly created demo_researcher has is_staff=False and is_superuser=False."""
        User.objects.filter(username="demo_researcher").delete()
        os.environ["DEMO_RESEARCHER_PASSWORD"] = "NonPrivPass123!"
        self.create_func(self.apps, None)
        user = User.objects.get(username="demo_researcher")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
