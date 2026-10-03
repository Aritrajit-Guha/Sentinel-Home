"""LangGraph node for ML assessment and personalized urgency scoring."""

from __future__ import annotations

from agent.graph.state import SentinelState, append_error, trace_event
from app.services.scoring_service import assess_household_risk
from agent.prompts.parameter_prompt import build_parameter_prompt


def assess_node(state: SentinelState) -> SentinelState:
    household = state.get("household")
    earthquake = state.get("earthquake")
    if not isinstance(household, dict) or not isinstance(earthquake, dict):
        return append_error(state, "household and earthquake are required for assessment")
    prompt = build_parameter_prompt(household=household, earthquake=earthquake)
    traced = trace_event(
        state,
        stage="parameter_generation",
        status="running",
        title="Preparing ML parameters",
        detail="Building the LLM prompt from the earthquake response and registered building facts.",
        request={"prompt": prompt},
    )
    try:
        assessment = assess_household_risk(household, earthquake)
    except Exception as exc:
        return append_error(trace_event(traced, stage="ml_inference", status="failed", title="ML assessment failed", error=str(exc)), f"assessment failed: {exc}")
    traced = trace_event(
        traced,
        stage="ml_inference",
        status="completed",
        title="XGBoost damage and urgency assessment",
        request={"validated_parameters": assessment.get("parameters", {})},
        response={key: value for key, value in assessment.items() if key != "parameters"},
    )
    return {**traced, "assessment": assessment, "silent": assessment.get("urgency_level") == "low"}
