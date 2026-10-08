import unittest

from app.core.store import alerts, households, users
from app.main import app


class AuthTests(unittest.TestCase):
    def setUp(self):
        users.clear(); households.clear(); alerts.clear()
        self.client = app.test_client()

    def tearDown(self):
        users.clear(); households.clear(); alerts.clear()

    def test_account_login_and_me(self):
        created = self.client.post("/api/auth/register", json={"email": "owner@example.com", "password": "password123"})
        self.assertEqual(created.status_code, 201)
        self.assertNotIn("password_hash", created.get_json()["user"])
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        logged_in = self.client.post("/api/auth/login", json={"email": "owner@example.com", "password": "password123"})
        self.assertEqual(logged_in.status_code, 200)

    def test_registration_requires_account_but_duplicate_payload_is_validated_first(self):
        response = self.client.post("/api/households", json={
            "location": "Durgapur", "latitude": 23.5, "longitude": 87.3,
            "building_type": "Masonry", "household_size": 2,
            "emergency_contact": {"name": "User", "phone": "+919876543210"},
            "primary_contact": {"name": "User", "phone": "+919876543210"},
            "relatives": [{"name": "Parent", "relationship": "father", "phone": "+91 98765 43210"}],
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post("/api/households", json={
            "location": "Durgapur", "latitude": 23.5, "longitude": 87.3,
            "building_type": "Masonry", "household_size": 2,
            "emergency_contact": {"name": "User", "phone": "+919876543211"},
        }).status_code, 401)
