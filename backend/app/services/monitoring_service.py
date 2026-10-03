"""Scheduled hazard monitoring and agentic household assessment."""

from datetime import datetime, timezone

from agent.graph.build_graph import run_agent_workflow
from app.core.store import households
from app.services.hazard_fetcher import fetch_earthquake_data, nearby_earthquakes


def run_monitoring_cycle(earthquake_data: dict | None = None) -> dict:
    """Fetch hazards once and run each new event through LangGraph."""

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

        workflow = None
        if events:
            earthquake = events[0]
            event_id = earthquake.get("id")
            if event_id and household.get("last_assessed_event_id") != event_id:
                workflow = run_agent_workflow(household, earthquake)
                assessment = workflow.get("assessment")
                if assessment:
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

        households[household["id"]] = household
        results.append({
            "household_id": household["id"],
            "nearby_earthquake_count": len(events),
            "latest_earthquake": events[0] if events else None,
            "assessment": workflow.get("assessment") if workflow else None,
            "advice": workflow.get("advice") if workflow else None,
            "alert": workflow.get("alert") if workflow else None,
            "confirmation_status": workflow.get("confirmation_status") if workflow else None,
            "escalation_required": bool(workflow.get("escalation_required")) if workflow else False,
            "workflow_errors": list(workflow.get("errors", [])) if workflow else [],
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
