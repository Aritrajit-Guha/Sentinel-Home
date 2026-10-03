"""LangGraph node that persists a generated alert without forcing delivery."""

from __future__ import annotations

from agent.graph.state import SentinelState, append_error
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
        )
    except Exception as exc:
        return append_error(state, f"alert creation failed: {exc}")
    if settings.AUTO_SEND_ALERTS and alert.get("delivery_status") == "pending":
        try:
            alert = send_alert_whatsapp(household["id"], alert)
        except Exception as exc:
            alert = {**alert, "delivery_status": "failed", "delivery_error": str(exc)}
            return append_error({**state, "alert": alert}, f"WhatsApp delivery failed: {exc}")

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
