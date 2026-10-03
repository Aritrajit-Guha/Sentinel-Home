"""Scheduled hazard monitoring and agentic household assessment."""

from datetime import datetime, timezone
import hashlib
import json

from agent.graph.build_graph import run_agent_workflow
from app.core.store import households
from app.services.hazard_fetcher import fetch_earthquake_data, nearby_earthquakes


def _event_signature(event: dict) -> str:
    values = {
        "id": event.get("id"),
        "magnitude": event.get("magnitude"),
        "mmi": event.get("mmi"),
        "distance_km": event.get("distance_km"),
        "hypocentral_distance_km": event.get("hypocentral_distance_km"),
    }
    return hashlib.sha256(
        json.dumps(values, sort_keys=True).encode("utf-8")
    ).hexdigest()


def run_monitoring_cycle(earthquake_data: dict | None = None, event_callback=None) -> dict:
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
            signature = _event_signature(earthquake)
            should_assess = (
                event_id
                and (
                    household.get("last_assessed_event_id") != event_id
                    or household.get("last_assessment_signature") != signature
                )
            )
            if should_assess:
                workflow_callback = None
                if event_callback:
                    workflow_callback = lambda event, household_id=household["id"]: event_callback({
                        **event, "household_id": household_id,
                    })
                workflow = run_agent_workflow(household, earthquake, workflow_callback)
                assessment = workflow.get("assessment")
                workflow_errors = list(workflow.get("errors", []))
                if assessment:
                    household["last_assessment"] = {
                        "hazard": "earthquake",
                        "event_id": event_id,
                        "assessed_at": checked_at,
                        **assessment,
                    }
                    household["risk_score"] = assessment["urgency_score"]
                    household["risk_level"] = assessment["urgency_level"]
                    household["last_hazard"] = "earthquake"
                    household["last_hazard_at"] = checked_at
                # If advice/RAG failed before an alert was created, leave the
                # event eligible for retry on the next scheduler cycle. An
                # existing alert means the assessment itself completed and
                # should not be duplicated merely because SMS delivery failed.
                if assessment and (not workflow_errors or workflow.get("alert")):
                    household["last_assessed_event_id"] = event_id
                    household["last_assessment_signature"] = signature
                household["last_workflow_errors"] = workflow_errors
                # The workflow may have changed the persisted household
                # (create_alert marks it unsafe). Do not overwrite that state
                # with the stale object captured before the workflow ran.
                workflow_household = workflow.get("household") or {}
                workflow_alert = workflow.get("alert") or {}
                if (
                    workflow_household.get("safe") is False
                    or workflow_alert.get("status") in {"active", "escalation_pending"}
                ):
                    household["safe"] = False

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
            "trace": list(workflow.get("trace", [])) if workflow else [],
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
