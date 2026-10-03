"""Notification boundary for Twilio SMS and voice delivery."""

import re
import json

from twilio.rest import Client
from app.core.config import settings


class NotificationConfigurationError(RuntimeError):
    """Raised when delivery is requested without Twilio configuration."""


def _client() -> Client:
    if not settings.TWILIO_SID or not settings.TWILIO_TOKEN:
        raise NotificationConfigurationError("Twilio credentials are not configured")
    return Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)


def _from_number() -> str:
    if not settings.TWILIO_FROM_NUMBER:
        raise NotificationConfigurationError("TWILIO_FROM_NUMBER is not configured")
    return settings.TWILIO_FROM_NUMBER


def _e164(value: str) -> str:
    """Normalize a user-entered international number for Twilio."""

    raw = str(value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits:
        raise ValueError("A phone number is required")
    return f"+{digits}"


def send_sms(to: str, body: str):
    if not to or not body:
        raise ValueError("SMS recipient and body are required")
    return _client().messages.create(body=body, from_=_from_number(), to=_e164(to))


def send_whatsapp(to: str, body: str):
    if not to or not body:
        raise ValueError("WhatsApp recipient and body are required")
    if not settings.TWILIO_WHATSAPP_FROM:
        raise NotificationConfigurationError("TWILIO_WHATSAPP_FROM is not configured")
    recipient = f"whatsapp:{_e164(to.removeprefix('whatsapp:'))}"
    sender = settings.TWILIO_WHATSAPP_FROM.strip()
    if not sender.startswith("whatsapp:"):
        sender = f"whatsapp:{sender}"
    payload = {"from_": sender, "to": recipient}
    content_sid = settings.TWILIO_WHATSAPP_CONTENT_SID.strip()
    if content_sid:
        payload["content_sid"] = content_sid
        payload["content_variables"] = json.dumps({"1": body})
    else:
        payload["body"] = body
    return _client().messages.create(**payload)


def make_call(to: str, twiml_url: str):
    if not to or not twiml_url:
        raise ValueError("call recipient and TwiML URL are required")
    return _client().calls.create(url=twiml_url, to=_e164(to), from_=_from_number())


def voice_url_for(alert_id: str, household_id: str) -> str:
    """Return the configured TwiML URL for an alert voice call."""

    if settings.TWILIO_VOICE_URL:
        return settings.TWILIO_VOICE_URL
    if settings.PUBLIC_BACKEND_URL:
        return (
            f"{settings.PUBLIC_BACKEND_URL}/api/alerts/"
            f"{household_id}/{alert_id}/voice"
        )
    raise NotificationConfigurationError(
        "TWILIO_VOICE_URL or PUBLIC_BACKEND_URL is required for voice escalation"
    )
