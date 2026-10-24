"""Tests for production monitoring history exposed to the household dashboard."""

import unittest

from app.core.store import households, monitoring_runs
from app.main import create_app
from app.services.monitoring_service import run_monitoring_cycle


class MonitoringDashboardTests(unittest.TestCase):
    def setUp(self):
        households.clear()
        monitoring_runs.clear()
        self.client = create_app().test_client()
        households["dashboard-household"] = {
            "id": "dashboard-household",
            "latitude": 23.52,
            "longitude": 87.31,
            "household_size": 2,
            "vulnerable_members": [],
            "safe": True,
        }

    def tearDown(self):
        households.clear()
        monitoring_runs.clear()

    def test_live_cycles_are_persisted_and_status_returns_latest_five(self):
        for _ in range(6):
            run_monitoring_cycle({"features": []})

        response = self.client.get("/api/households/dashboard-household/status")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["recent_checks"]), 5)
        self.assertEqual(payload["current_cycle_state"], "completed")
        self.assertEqual(payload["last_check"]["source"], "live")
        self.assertIn("scheduler", payload)
        self.assertIn("next_run_at", payload["scheduler"])

    def test_simulation_cycles_do_not_enter_production_history(self):
        run_monitoring_cycle({"features": []}, simulation=True)

        response = self.client.get("/api/households/dashboard-household/status")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["recent_checks"], [])
        self.assertIsNone(payload["last_check"])
        self.assertEqual(payload["current_cycle_state"], "no_history")


if __name__ == "__main__":
    unittest.main()
