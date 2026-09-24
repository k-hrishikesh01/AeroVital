from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Pilot


class PilotModelAndAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testpilot", password="password123")
        self.client = APIClient()

    def test_unauthenticated_request_rejected(self):
        response = self.client.get("/api/v1/pilots/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_obtain_auth_token_success(self):
        response = self.client.post("/api/v1/auth/token/", {
            "username": "testpilot",
            "password": "password123",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_obtain_auth_token_invalid_credentials(self):
        response = self.client.post("/api/v1/auth/token/", {
            "username": "testpilot",
            "password": "wrongpassword",
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pilot_crud_authenticated(self):
        self.client.force_authenticate(user=self.user)

        # Create
        post_data = {
            "pilot_code": "VIPER-01",
            "name": "Capt. Pete Mitchell",
            "age": 34,
            "sex": "M",
            "is_active": True,
        }
        res = self.client.post("/api/v1/pilots/", post_data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        pilot_id = res.data["id"]

        # List
        res_list = self.client.get("/api/v1/pilots/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.data), 1)

        # Detail
        res_detail = self.client.get(f"/api/v1/pilots/{pilot_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["pilot_code"], "VIPER-01")

        # Update
        patch_res = self.client.patch(f"/api/v1/pilots/{pilot_id}/", {"age": 35})
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["age"], 35)

    def test_pilot_cannot_access_other_pilot_profile(self):
        user_a = User.objects.create_user(username="pilota", password="password123")
        pilot_a = Pilot.objects.create(
            user=user_a,
            pilot_code="PILOT-A",
            name="Pilot Alpha",
            age=28,
            sex="M",
        )

        user_b = User.objects.create_user(username="pilotb", password="password123")
        pilot_b = Pilot.objects.create(
            user=user_b,
            pilot_code="PILOT-B",
            name="Pilot Bravo",
            age=32,
            sex="F",
        )

        client_a = APIClient()
        client_a.force_authenticate(user=user_a)

        # Pilot A accessing own profile -> OK
        res_own = client_a.get(f"/api/v1/pilots/{pilot_a.id}/")
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)

        # Pilot A attempting to access Pilot B's profile -> 403 Forbidden
        res_other = client_a.get(f"/api/v1/pilots/{pilot_b.id}/")
        self.assertEqual(res_other.status_code, status.HTTP_403_FORBIDDEN)
