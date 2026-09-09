"""Backend monitoring cycle before ML/agent decisions are introduced."""

from datetime import datetime, timezone

from app.core.store import households
from app.services.hazard_fetcher import fetch_earthquake_data, nearby_earthquakes


def run_monitoring_cycle(earthquake_data: dict | None = None) -> dict:
    """Fetch earthquake data once and update each household's hazard context.

    This service deliberately stops before scoring or alert creation. The ML
    and agent layers can consume the returned household records later.
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
        households[household["id"]] = household

        results.append({
            "household_id": household["id"],
            "nearby_earthquake_count": len(events),
            "latest_earthquake": events[0] if events else None,
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
