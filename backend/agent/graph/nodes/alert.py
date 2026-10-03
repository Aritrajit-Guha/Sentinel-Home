"""LangGraph node that persists a generated alert without forcing delivery."""

from __future__ import annotations

from agent.graph.state import SentinelState, append_error
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
        )
    except Exception as exc:
        return append_error(state, f"alert creation failed: {exc}")
    return {**state, "alert": alert, "confirmation_status": "pending"}
