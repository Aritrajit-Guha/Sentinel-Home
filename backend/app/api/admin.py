from flask import Blueprint, jsonify, request

from app.core.store import alerts, households
from app.services.hazard_fetcher import fetch_earthquake_data, fetch_weather_data
from app.services.monitoring_service import run_monitoring_cycle
from app.scheduling.scheduler import scheduler_status, start_scheduler, stop_scheduler


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/status")
def system_status():
    scheduler = scheduler_status()
    alert_count = sum(
        len(household_alerts)
        for household_alerts in alerts.values()
    )
    return jsonify({
        "status": "running",
        "households_registered": len(households),
        "monitoring": "scheduled" if scheduler["running"] else "manual",
        "persistence": households.mode,
        "alerts_tracked": alert_count,
        "scheduler": scheduler,
    })


@admin_bp.get("/hazards/earthquakes")
def current_earthquakes():
    try:
        return jsonify(fetch_earthquake_data())
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502


@admin_bp.post("/monitoring/run")
def run_monitoring():
    try:
        result = run_monitoring_cycle()
        return jsonify({"status": "completed", **result})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502


@admin_bp.post("/scheduler/start")
def start_monitoring_scheduler():
    try:
        started = start_scheduler()
        return jsonify({
            "status": "started" if started else "already_running",
            "scheduler": scheduler_status(),
        })
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@admin_bp.post("/scheduler/stop")
def stop_monitoring_scheduler():
    stopped = stop_scheduler()
    return jsonify({
        "status": "stopped" if stopped else "already_stopped",
        "scheduler": scheduler_status(),
    })


@admin_bp.get("/hazards/weather")
def current_weather():
    try:
        latitude = float(request.args["latitude"])
        longitude = float(request.args["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "latitude and longitude query parameters are required",
        }), 400

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return jsonify({
            "status": "error",
            "message": "latitude or longitude is outside the valid range",
        }), 400

    try:
        data = fetch_weather_data(latitude, longitude)
        return jsonify({
            "status": "ok",
            "latitude": latitude,
            "longitude": longitude,
            "weather": data,
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 502
