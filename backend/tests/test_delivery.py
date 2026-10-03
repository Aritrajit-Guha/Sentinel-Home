"""Tests for automatic alert delivery and timeout escalation."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from app.core.store import alerts, households
from app.services.alert_service import create_alert
from app.services.delivery_service import process_pending_alerts


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        households.clear()
        alerts.clear()
        households["delivery-household"] = {
            "id": "delivery-household",
            "emergency_contact": "+10000000000",
            "safe": False,
        }

    def tearDown(self):
        households.clear()
        alerts.clear()

    def test_pending_alert_is_sent_when_auto_delivery_enabled(self):
        create_alert(
            "delivery-household",
            hazard="earthquake",
            risk_score=0.8,
            message="Take shelter.",
            event_id="event-1",
        )
        fake_message = type("Message", (), {"sid": "SM-test"})()
        with patch("app.services.delivery_service.settings.AUTO_SEND_ALERTS", True), \
             patch("app.services.delivery_service.settings.TWILIO_WHATSAPP_FROM", ""), \
             patch("app.services.delivery_service.notification_service.send_sms", return_value=fake_message):
            result = process_pending_alerts()
        self.assertEqual(result["sms_sent"], 1)
        self.assertEqual(alerts["delivery-household"][0]["delivery_status"], "sent")

    def test_expired_alert_is_escalated_when_enabled(self):
        alert = create_alert(
            "delivery-household",
            hazard="earthquake",
            risk_score=0.8,
            message="Take shelter.",
            event_id="event-2",
        )
        alert["created_at"] = (
            datetime.now(timezone.utc) - timedelta(minutes=10)
        ).isoformat()
        alerts["delivery-household"] = [alert]
        fake_call = type("Call", (), {"sid": "CA-test"})()
        with patch("app.services.delivery_service.settings.AUTO_ESCALATE_ALERTS", True), \
             patch("app.services.delivery_service.settings.ALERT_CONFIRMATION_TIMEOUT_MINUTES", 1), \
             patch("app.services.delivery_service.notification_service.voice_url_for", return_value="https://example.test/voice"), \
             patch("app.services.delivery_service.notification_service.make_call", return_value=fake_call):
            result = process_pending_alerts()
        self.assertEqual(result["voice_escalations"], 1)
        self.assertEqual(alerts["delivery-household"][0]["status"], "escalated")
