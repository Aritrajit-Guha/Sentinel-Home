"""LangGraph node that persists a generated alert without forcing delivery."""

from __future__ import annotations

from agent.graph.state import SentinelState, append_error, trace_event
from app.core.config import settings
from app.services.delivery_service import send_alert_whatsapp
from app.services.alert_service import create_alert


def alert_node(state: SentinelState) -> SentinelState:
    household = state.get("household")
    assessment = state.get("assessment")
    advice = state.get("advice")
    if not all(isinstance(value, dict) for value in (household, assessment, advice)):
        return append_error(state, "alert creation requires household, assessment, and advice")
    try:
        alert = create_alert(
            household["id"], hazard="earthquake",
            risk_score=assessment["urgency_score"],
            message=advice["message"], sources=advice.get("sources", []),
            event_id=state.get("earthquake", {}).get("id"),
            simulation=bool(state.get("simulation")),
        )
    except Exception as exc:
        return append_error(state, f"alert creation failed: {exc}")
    if settings.AUTO_SEND_ALERTS and alert.get("delivery_status") == "pending":
        try:
            alert = send_alert_whatsapp(household["id"], alert)
        except Exception as exc:
            alert = {**alert, "delivery_status": "failed", "delivery_error": str(exc)}
            failed_state = trace_event(state, stage="notification", status="failed", title="Telegram/notification delivery", error=str(exc))
            return append_error({**failed_state, "alert": alert}, f"Notification delivery failed: {exc}")

        delivery = (alert.get("deliveries") or [])[-1:]
        state = trace_event(
            state,
            stage="notification",
            status="completed",
            title="Alert delivered to configured notification channel",
            request={"channel": alert.get("delivery_channel"), "recipient": delivery[0].get("phone") if delivery else None},
            response={"delivery_status": alert.get("delivery_status"), "provider_id": alert.get("delivery_id")},
        )

    state = trace_event(
        state,
        stage="alert_persistence",
        status="completed",
        title="Alert saved to MongoDB",
        request={"risk_score": assessment.get("urgency_score"), "event_id": state.get("earthquake", {}).get("id")},
        response={"alert_id": alert.get("id"), "status": alert.get("status"), "delivery_status": alert.get("delivery_status")},
    )

    # create_alert persists safe=False, but the household object carried in
    # the graph state is a copy from before persistence. Keep the graph state
    # consistent so observe_node waits for confirmation instead of treating a
    # newly-created alert as already confirmed.
    updated_household = {**household, "safe": False}
    return {
        **state,
        "household": updated_household,
        "alert": alert,
        "confirmation_status": "pending",
    }
