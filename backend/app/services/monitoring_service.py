"""Scheduled hazard monitoring and pre-agent risk assessment."""

from datetime import datetime, timezone

from app.core.store import households
from app.services.hazard_fetcher import fetch_earthquake_data, nearby_earthquakes
from app.services.scoring_service import assess_household_risk


def run_monitoring_cycle(earthquake_data: dict | None = None) -> dict:
    """Fetch earthquake data once and update each household's hazard context.

    This service performs parameter generation, ML assessment, and urgency
    scoring. Alert advice and agentic escalation remain separate stages.
    """
    checked_at = datetime.now(timezone.utc).isoformat()
    payload = earthquake_data if earthquake_data is not None else fetch_earthquake_data()
    results = []

    for household in households.values():
        events = nearby_earthquakes(
            household["latitude"],
            household["longitude"],
            earthquake_data=payload,
        )
        household["last_monitored_at"] = checked_at
        household["nearby_earthquake_count"] = len(events)
        household["latest_earthquake"] = events[0] if events else None
        household["updated_at"] = checked_at

        assessment = None
        assessment_error = None
        if events:
            earthquake = events[0]
            event_id = earthquake.get("id")
            if event_id and household.get("last_assessed_event_id") != event_id:
                try:
                    assessment = assess_household_risk(household, earthquake)
                    household["last_assessment"] = {
                        "hazard": "earthquake",
                        "event_id": event_id,
                        "assessed_at": checked_at,
                        **assessment,
                    }
                    household["last_assessed_event_id"] = event_id
                    household["risk_score"] = assessment["urgency_score"]
                    household["risk_level"] = assessment["urgency_level"]
                    household["last_hazard"] = "earthquake"
                    household["last_hazard_at"] = checked_at
                except Exception as exc:
                    assessment_error = str(exc)

        households[household["id"]] = household

        results.append({
            "household_id": household["id"],
            "nearby_earthquake_count": len(events),
            "latest_earthquake": events[0] if events else None,
            "assessment": assessment,
            "assessment_error": assessment_error,
        })

    return {
        "checked_at": checked_at,
        "earthquake_events_received": len(payload.get("features", [])),
        "households_checked": len(results),
        "households_with_nearby_earthquakes": sum(
            result["nearby_earthquake_count"] > 0 for result in results
        ),
        "households": results,
    }
