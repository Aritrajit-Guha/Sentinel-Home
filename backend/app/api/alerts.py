from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.core.store import alerts, households
from app.services import notification_service
from app.services.alert_service import create_alert, get_alert, is_simulation_alert
from app.services.alert_service import update_alert
from app.services.delivery_service import escalate_alert_voice, send_alert_whatsapp
from app.services.contact_service import primary_contact


alerts_bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")
ALLOWED_HAZARDS = {"earthquake", "flood", "cyclone", "general"}


@alerts_bp.post("/<household_id>")
def create_household_alert(household_id):
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "message": "request body must be a JSON object"}), 400
    missing = [
        field for field in ("hazard", "message")
        if not isinstance(payload.get(field), str)
        or not payload[field].strip()
    ]
    if missing:
        return jsonify({
            "status": "error",
            "errors": [f"{field} is required" for field in missing],
        }), 400

    if household_id not in households:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    hazard = payload["hazard"].strip().lower()
    if hazard not in ALLOWED_HAZARDS:
        return jsonify({
            "status": "error",
            "message": f"hazard must be one of: {sorted(ALLOWED_HAZARDS)}",
        }), 400

    if "sources" in payload and not isinstance(payload["sources"], list):
        return jsonify({
            "status": "error",
            "message": "sources must be a list",
        }), 400

    if payload.get("risk_score") is not None:
        try:
            risk_score = float(payload["risk_score"])
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "risk_score must be numeric"}), 400
        if not 0 <= risk_score <= 1:
            return jsonify({
                "status": "error",
                "message": "risk_score must be between 0 and 1",
            }), 400

    try:
        alert = create_alert(
            household_id,
            hazard=hazard,
            risk_score=payload.get("risk_score"),
            message=payload["message"].strip(),
            sources=payload.get("sources", []),
            event_id=payload.get("event_id"),
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    return jsonify({"status": "created", "alert": alert}), 201


@alerts_bp.post("/<household_id>/confirm-safe")
def confirm_safe(household_id):
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    household["safe"] = True
    household["safe_at"] = datetime.now(timezone.utc).isoformat()

    household_alerts = alerts.get(household_id, [])
    for alert in household_alerts:
        if alert["status"] == "active" and not is_simulation_alert(alert):
            alert["status"] = "confirmed"
            alert["confirmed_at"] = household["safe_at"]
    households[household_id] = household
    alerts[household_id] = household_alerts

    return jsonify({
        "status": "confirmed",
        "household_id": household_id,
        "alerts": [alert for alert in household_alerts if not is_simulation_alert(alert)],
    })


@alerts_bp.get("/<household_id>")
def household_alerts(household_id):
    if household_id not in households:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    return jsonify({
        "status": "ok",
        "household_id": household_id,
        "alerts": [alert for alert in alerts.get(household_id, []) if not is_simulation_alert(alert)],
    })


@alerts_bp.get("/<household_id>/<alert_id>")
def get_household_alert(household_id, alert_id):
    if household_id not in households:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    alert = get_alert(household_id, alert_id)
    if alert is None:
        return jsonify({"status": "error", "message": "Alert not found"}), 404

    return jsonify({"status": "ok", "alert": alert})


@alerts_bp.post("/<household_id>/<alert_id>/send")
def send_alert(household_id, alert_id):
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    alert = get_alert(household_id, alert_id)
    if alert is None:
        return jsonify({"status": "error", "message": "Alert not found"}), 404
    if alert["status"] != "active":
        return jsonify({
            "status": "error",
            "message": "Only active alerts can be sent",
        }), 409

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "message": "request body must be a JSON object"}), 400
    channel = payload.get("channel", "whatsapp")
    if channel not in {"whatsapp", "telegram", "sms"}:
        return jsonify({
            "status": "error",
            "message": "channel must be whatsapp or sms",
        }), 400

    try:
        if channel in {"whatsapp", "telegram"}:
            return jsonify({"status": "sent", "alert": send_alert_whatsapp(household_id, alert)})
        contact = primary_contact(household)
        if not contact:
            return jsonify({"status": "error", "message": "A primary contact is required"}), 400
        message = notification_service.send_sms(
            contact["phone"],
            alert["message"],
        )
    except notification_service.NotificationConfigurationError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 503
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502

    sent_at = datetime.now(timezone.utc).isoformat()
    alert.update({
        "delivery_status": "sent",
        "delivery_channel": "sms",
        "sent_at": sent_at,
        "delivery_id": getattr(message, "sid", None),
    })
    alerts[household_id] = alerts.get(household_id, [])
    return jsonify({"status": "sent", "alert": alert})


@alerts_bp.post("/<household_id>/<alert_id>/escalate")
def escalate_alert(household_id, alert_id):
    """Escalate an unanswered active alert through a voice call."""
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    alert = get_alert(household_id, alert_id)
    if alert is None:
        return jsonify({"status": "error", "message": "Alert not found"}), 404
    if alert["status"] != "active":
        return jsonify({
            "status": "error",
            "message": "Only active alerts can be escalated",
        }), 409

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "message": "request body must be a JSON object"}), 400
    twiml_url = payload.get("twiml_url")
    if twiml_url is not None and (not isinstance(twiml_url, str) or not twiml_url.strip()):
        return jsonify({"status": "error", "message": "twiml_url must be a URL when provided"}), 400

    try:
        return jsonify({
            "status": "escalated",
            "alert": escalate_alert_voice(household_id, alert, twiml_url.strip() if twiml_url else None),
        })
    except notification_service.NotificationConfigurationError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 503
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502

    escalated_at = datetime.now(timezone.utc).isoformat()
    alert.update({
        "delivery_status": "escalated",
        "delivery_channel": "voice",
        "escalated_at": escalated_at,
        "escalation_count": alert.get("escalation_count", 0) + 1,
        "delivery_id": getattr(call, "sid", None),
    })
    alerts[household_id] = alerts.get(household_id, [])
    return jsonify({"status": "escalated", "alert": alert})


@alerts_bp.get("/<household_id>/<alert_id>/voice")
def alert_voice_message(household_id, alert_id):
    """Return TwiML for Twilio's voice escalation callback."""
    from html import escape
    from flask import Response

    if household_id not in households:
        return jsonify({"status": "error", "message": "Household not found"}), 404
    alert = get_alert(household_id, alert_id)
    if alert is None:
        return jsonify({"status": "error", "message": "Alert not found"}), 404

    message = escape(alert.get("message", "Please check your SentinelHome alert."))
    alert = update_alert(
        household_id,
        alert_id,
        voice_callback_at=datetime.now(timezone.utc).isoformat(),
    ) or alert
    xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        f"<Response><Say language=\"en-IN\">{message}</Say></Response>"
    )
    return Response(xml, mimetype="text/xml")
