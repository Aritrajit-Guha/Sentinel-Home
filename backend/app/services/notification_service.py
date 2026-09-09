# Phase 6: sends SMS/call via Twilio
from twilio.rest import Client
from app.core.config import settings

def send_sms(to: str, body: str):
    client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
    return client.messages.create(body=body, from_="+1XXXXXXXXXX", to=to)

def make_call(to: str, twiml_url: str):
    client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
    return client.calls.create(url=twiml_url, to=to, from_="+1XXXXXXXXXX")
