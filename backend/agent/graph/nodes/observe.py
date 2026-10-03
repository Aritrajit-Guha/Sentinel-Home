"""Non-blocking confirmation observation node."""

from __future__ import annotations

from datetime import datetime, timezone

from agent.graph.state import SentinelState


def observe_node(state: SentinelState) -> SentinelState:
    household = state.get("household", {})
    alert = state.get("alert", {})
    if household.get("safe") is True or alert.get("status") == "confirmed":
        return {**state, "confirmation_status": "confirmed", "completed": True}
    created_at = alert.get("created_at")
    timeout_seconds = float(household.get("confirmation_timeout_seconds", 0) or 0)
    if created_at and timeout_seconds > 0:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - created).total_seconds() >= timeout_seconds:
                return {**state, "confirmation_status": "timeout", "escalation_required": True}
        except (TypeError, ValueError):
            pass
    return {**state, "confirmation_status": "pending", "completed": True}
