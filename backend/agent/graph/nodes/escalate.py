"""Escalation decision node for unanswered alerts."""

from agent.graph.state import SentinelState


def escalate_node(state: SentinelState) -> SentinelState:
    alert = dict(state.get("alert", {}))
    if alert:
        alert["escalation_required"] = True
        alert["status"] = "escalation_pending"
    return {**state, "alert": alert, "escalation_required": True, "completed": True}
