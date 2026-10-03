"""Focused tests for the pre-delivery SentinelHome agent workflow."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from agent.graph.build_graph import run_agent_workflow
from app.core.store import alerts, households


def _household(**overrides):
    value = {
        "id": "test-household",
        "latitude": 23.52,
        "longitude": 87.31,
        "household_size": 3,
        "vulnerable_members": [],
        "safe": True,
    }
    value.update(overrides)
    households[value["id"]] = value
    return value


def _earthquake():
    return {
        "id": "test-earthquake",
        "magnitude": 5.0,
        "mmi": 6.9,
        "distance_km": 40.0,
        "hypocentral_distance_km": 55.0,
        "depth_km": 36.8,
        "latitude": 22.5,
        "longitude": 89.1,
    }


def _assessment(level="high"):
    return {
        "parameters": {},
        "damage_grade": 4,
        "damage_probabilities": {"1": 0.05, "2": 0.10, "3": 0.20, "4": 0.50, "5": 0.15},
        "physical_damage_risk": 0.72,
        "hazard_score": 0.80,
        "vulnerability_score": 0.20,
        "urgency_score": 0.78 if level == "high" else 0.10,
        "urgency_level": level,
    }


class AgentWorkflowTests(unittest.TestCase):
    def tearDown(self):
        households.clear()
        alerts.clear()

    def test_low_risk_takes_silent_branch(self):
        household = _household()
        with patch("agent.graph.nodes.assess.assess_household_risk", return_value=_assessment("low")):
            result = run_agent_workflow(household, _earthquake())
        self.assertTrue(result["silent"])
        self.assertTrue(result["completed"])
        self.assertNotIn("advice", result)


    def test_high_risk_retrieves_advice_and_creates_alert(self):
        household = _household(safe=False)
        advice = {"message": "Move to a safer location.", "sources": [{"source": "guide.pdf", "page": 1}], "grounded": True}
        with patch("agent.graph.nodes.assess.assess_household_risk", return_value=_assessment("high")), \
             patch("agent.graph.nodes.advise.generate_advice_for_household", return_value=advice), \
             patch("agent.graph.nodes.alert.settings.AUTO_SEND_ALERTS", False):
            result = run_agent_workflow(household, _earthquake())
        self.assertEqual(result["alert"]["message"], advice["message"])
        self.assertEqual(result["confirmation_status"], "pending")
        self.assertTrue(alerts.get(household["id"]))


    def test_expired_alert_marks_escalation_required(self):
        created_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        household = _household(safe=False, confirmation_timeout_seconds=60)
        advice = {"message": "Evacuate carefully.", "sources": [], "grounded": False}
        with patch("agent.graph.nodes.assess.assess_household_risk", return_value=_assessment("high")), \
             patch("agent.graph.nodes.advise.generate_advice_for_household", return_value=advice), \
             patch("agent.graph.nodes.alert.create_alert", return_value={
                 "id": "alert-1", "status": "active", "created_at": created_at,
                 "message": advice["message"],
             }):
            result = run_agent_workflow(household, _earthquake())
        self.assertEqual(result["confirmation_status"], "timeout")
        self.assertTrue(result["escalation_required"])
        self.assertEqual(result["alert"]["status"], "escalation_pending")

    def test_provider_failure_keeps_high_risk_alert_path_alive(self):
        from agent.graph.nodes.advise import _fallback_advice

        result = _fallback_advice(
            "earthquake guidance",
            sources=[{"source": "guide.pdf", "page": 1}],
            error=RuntimeError("503 unavailable"),
        )
        self.assertTrue(result["degraded"])
        self.assertEqual(result["sources"][0]["source"], "guide.pdf")
        self.assertIn("503 unavailable", result["generation_error"])

    def test_parameter_provider_failure_uses_validated_fallback(self):
        from agent.tools.model_parameter_tool import generate_parameters_for_household

        household = {
            "count_floors_pre_eq": 2,
            "age_building": 30,
            "superstructure_materials": ["adobe_mud"],
        }
        earthquake = {
            "magnitude": 7.5,
            "distance_km": 12.0,
            "hypocentral_distance_km": 15.0,
            "mmi": 8.0,
        }
        with patch(
            "agent.tools.model_parameter_tool.generate_model_parameters",
            side_effect=RuntimeError("503 unavailable"),
        ):
            result = generate_parameters_for_household(household, earthquake)

        self.assertEqual(result["count_floors_pre_eq"], 2)
        self.assertEqual(result["magnitude"], 7.5)
        self.assertEqual(result["epicentral_distance_km"], 12.0)
        self.assertEqual(result["has_superstructure_adobe_mud"], 1)
