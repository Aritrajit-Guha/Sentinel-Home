"""LangGraph node for ML assessment and personalized urgency scoring."""

from __future__ import annotations

from agent.graph.state import SentinelState, append_error
from app.services.scoring_service import assess_household_risk


def assess_node(state: SentinelState) -> SentinelState:
    household = state.get("household")
    earthquake = state.get("earthquake")
    if not isinstance(household, dict) or not isinstance(earthquake, dict):
        return append_error(state, "household and earthquake are required for assessment")
    try:
        assessment = assess_household_risk(household, earthquake)
    except Exception as exc:
        return append_error(state, f"assessment failed: {exc}")
    return {**state, "assessment": assessment, "silent": assessment.get("urgency_level") == "low"}
