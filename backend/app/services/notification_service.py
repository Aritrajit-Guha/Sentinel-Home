"""Notification boundary for Twilio SMS and voice delivery."""

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


def send_sms(to: str, body: str):
    if not to or not body:
        raise ValueError("SMS recipient and body are required")
    return _client().messages.create(body=body, from_=_from_number(), to=to)


def make_call(to: str, twiml_url: str):
    if not to or not twiml_url:
        raise ValueError("call recipient and TwiML URL are required")
    return _client().calls.create(url=twiml_url, to=to, from_=_from_number())
