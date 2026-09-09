from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, jsonify, request

from app.core.store import alerts, households
from app.models.household import validate_household
from app.services.alert_service import risk_level_for
from app.services.geocoding_service import geocode
from app.services.hazard_fetcher import fetch_weather_data, nearby_earthquakes


households_bp = Blueprint("households", __name__, url_prefix="/api/households")


@households_bp.get("/geocode")
def geocode_household_location():
    address = request.args.get("address", "").strip()
    if not address:
        return jsonify({
            "status": "error",
            "message": "address query parameter is required",
        }), 400
    if len(address) < 3 or len(address) > 250:
        return jsonify({
            "status": "error",
            "message": "address must contain between 3 and 250 characters",
        }), 400

    try:
        results = geocode(address)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502

    locations = []
    for result in results[:5]:
        try:
            locations.append({
                "display_name": result.get("display_name"),
                "latitude": float(result["lat"]),
                "longitude": float(result["lon"]),
                "osm_type": result.get("osm_type"),
                "osm_id": result.get("osm_id"),
            })
        except (KeyError, TypeError, ValueError):
            continue

    return jsonify({
        "status": "ok",
        "query": address,
        "count": len(locations),
        "locations": locations,
    })


@households_bp.get("", strict_slashes=False)
def list_households():
    return jsonify({
        "status": "ok",
        "count": len(households),
        "households": list(households.values()),
    })


@households_bp.post("", strict_slashes=False)
def register_household():
    payload = request.get_json(silent=True) or {}
    errors = validate_household(payload)
    if errors:
        return jsonify({"status": "error", "errors": errors}), 400

    household_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    household = {
        "id": household_id,
        **payload,
        "latitude": float(payload["latitude"]),
        "longitude": float(payload["longitude"]),
        "household_size": int(payload["household_size"]),
        "vulnerable_members": payload.get("vulnerable_members", []),
        "safe": True,
        "risk_score": None,
        "risk_level": "unknown",
        "last_hazard": None,
        "last_hazard_at": None,
        "created_at": now,
        "updated_at": now,
    }
    households[household_id] = household
    return jsonify({"status": "registered", "household": household}), 201


@households_bp.get("/<household_id>")
def get_household(household_id):
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404
    return jsonify({"status": "ok", "household": household})


@households_bp.get("/<household_id>/status")
def get_household_status(household_id):
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    household_alerts = alerts.get(household_id, [])
    active_alerts = [alert for alert in household_alerts if alert["status"] == "active"]
    if active_alerts:
        monitoring_state = "alert_active"
    elif household["safe"]:
        monitoring_state = "monitoring"
    else:
        monitoring_state = "awaiting_confirmation"

    return jsonify({
        "status": "ok",
        "household_id": household_id,
        "monitoring_state": monitoring_state,
        "safe": household["safe"],
        "risk_score": household.get("risk_score"),
        "risk_level": household.get("risk_level", "unknown"),
        "last_hazard": household.get("last_hazard"),
        "last_hazard_at": household.get("last_hazard_at"),
        "last_assessment": household.get("last_assessment"),
        "last_monitored_at": household.get("last_monitored_at"),
        "nearby_earthquake_count": household.get("nearby_earthquake_count", 0),
        "latest_earthquake": household.get("latest_earthquake"),
        "active_alerts": active_alerts,
        "recent_alerts": household_alerts[:5],
    })


@households_bp.post("/<household_id>/assessment")
def record_household_assessment(household_id):
    """Store an ML assessment without creating or closing an alert."""
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "message": "request body must be a JSON object"}), 400
    hazard = payload.get("hazard")
    if not isinstance(hazard, str) or not hazard.strip():
        return jsonify({"status": "error", "message": "hazard is required"}), 400

    hazard = hazard.strip().lower()
    if hazard not in {"earthquake", "flood", "cyclone", "general"}:
        return jsonify({
            "status": "error",
            "message": "hazard must be earthquake, flood, cyclone, or general",
        }), 400

    try:
        risk_score = float(payload["risk_score"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"status": "error", "message": "risk_score must be numeric"}), 400

    if not 0 <= risk_score <= 1:
        return jsonify({
            "status": "error",
            "message": "risk_score must be between 0 and 1",
        }), 400

    assessed_at = datetime.now(timezone.utc).isoformat()
    risk_level = risk_level_for(risk_score)
    assessment = {
        "hazard": hazard,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "assessed_at": assessed_at,
        "source": payload.get("source", "ml"),
    }
    household.update({
        "risk_score": risk_score,
        "risk_level": risk_level,
        "last_hazard": hazard,
        "last_hazard_at": assessed_at,
        "last_assessment": assessment,
        "updated_at": assessed_at,
    })
    households[household_id] = household

    return jsonify({
        "status": "recorded",
        "household_id": household_id,
        "assessment": assessment,
        "alert_required": risk_level == "high",
    })


@households_bp.get("/<household_id>/hazards/earthquakes")
def get_household_earthquakes(household_id):
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    try:
        radius_km = float(request.args.get("radius_km", 500))
        if radius_km <= 0 or radius_km > 20000:
            raise ValueError
        events = nearby_earthquakes(
            household["latitude"],
            household["longitude"],
            radius_km=radius_km,
        )
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "radius_km must be between 0 and 20000",
        }), 400
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502

    return jsonify({
        "status": "ok",
        "household_id": household_id,
        "radius_km": radius_km,
        "count": len(events),
        "earthquakes": events,
    })


@households_bp.get("/<household_id>/hazards/weather")
def get_household_weather(household_id):
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    try:
        weather = fetch_weather_data(
            household["latitude"],
            household["longitude"],
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502

    return jsonify({
        "status": "ok",
        "household_id": household_id,
        "latitude": household["latitude"],
        "longitude": household["longitude"],
        "weather": weather,
    })


@households_bp.patch("/<household_id>")
def update_household(household_id):
    household = households.get(household_id)
    if household is None:
        return jsonify({"status": "error", "message": "Household not found"}), 404

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"status": "error", "message": "request body must be a JSON object"}), 400
    candidate = {key: value for key, value in payload.items() if key != "id"}
    errors = validate_household(candidate, partial=True)
    if errors:
        return jsonify({"status": "error", "errors": errors}), 400

    household.update(candidate)
    if "latitude" in candidate:
        household["latitude"] = float(candidate["latitude"])
    if "longitude" in candidate:
        household["longitude"] = float(candidate["longitude"])
    if "household_size" in candidate:
        household["household_size"] = int(candidate["household_size"])
    household["updated_at"] = datetime.now(timezone.utc).isoformat()
    households[household_id] = household

    return jsonify({"status": "updated", "household": household})
