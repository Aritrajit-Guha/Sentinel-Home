"""Non-blocking confirmation observation node."""

from __future__ import annotations

from datetime import datetime, timezone

from agent.graph.state import SentinelState, trace_event
from app.core.config import settings


def observe_node(state: SentinelState) -> SentinelState:
    household = state.get("household", {})
    alert = state.get("alert", {})
    if household.get("safe") is True or alert.get("status") == "confirmed":
        return trace_event({**state, "confirmation_status": "confirmed", "completed": True}, stage="confirmation", status="completed", title="Household already confirmed safe", response={"escalation_prevented": True})
    created_at = alert.get("created_at")
    timeout_seconds = float(
        household.get(
            "confirmation_timeout_seconds",
            settings.ALERT_CONFIRMATION_TIMEOUT_MINUTES * 60,
        )
        or 0
    )
    if created_at and timeout_seconds > 0:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - created).total_seconds() >= timeout_seconds:
                return trace_event({**state, "confirmation_status": "timeout", "escalation_required": True}, stage="confirmation", status="timeout", title="Confirmation window expired", response={"escalation_required": True})
        except (TypeError, ValueError):
            pass
    return trace_event({**state, "confirmation_status": "pending", "completed": True}, stage="confirmation", status="pending", title="Waiting for household confirmation", response={"escalation_if_unconfirmed": True})
