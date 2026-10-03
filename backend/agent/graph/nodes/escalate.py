"""Escalation decision node for unanswered alerts."""

from agent.graph.state import SentinelState
from agent.graph.state import trace_event
from app.services.alert_service import update_alert


def escalate_node(state: SentinelState) -> SentinelState:
    alert = dict(state.get("alert", {}))
    if alert:
        alert["escalation_required"] = True
        alert["status"] = "escalation_pending"
        household = state.get("household", {})
        if household.get("id"):
            update_alert(household["id"], alert["id"], **{
                "escalation_required": True,
                "status": "escalation_pending",
            })
    return trace_event({**state, "alert": alert, "escalation_required": True, "completed": True}, stage="escalation", status="completed", title="Escalation queued for unanswered alert", response={"status": alert.get("status"), "escalation_required": True})
