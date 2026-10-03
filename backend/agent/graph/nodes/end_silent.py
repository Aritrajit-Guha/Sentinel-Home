"""Terminal node for assessments below the alert threshold."""

from agent.graph.state import SentinelState


def end_silent_node(state: SentinelState) -> SentinelState:
    return {**state, "silent": True, "completed": True}

