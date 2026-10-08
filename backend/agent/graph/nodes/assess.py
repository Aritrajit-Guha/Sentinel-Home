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
        status="started",
        title="Preparing ML parameters",
        detail="Building the LLM prompt from the earthquake response and registered building facts.",
        request={"prompt": prompt},
    )
    try:
        assessment = assess_household_risk(household, earthquake)
    except Exception as exc:
        return append_error(trace_event(traced, stage="parameter_generation", status="failed", title="ML parameter generation failed", error=str(exc)), f"assessment failed: {exc}")
    traced = trace_event(
        traced,
        stage="parameter_generation",
        status="completed",
        title="Validated ML parameters generated",
        detail="The parameter payload passed validation and is ready for XGBoost.",
        response={"parameters": assessment.get("parameters", {}), "valid": True},
    )
    traced["trace"][-1]["provider"] = (assessment.get("parameter_generation") or {}).get("provider", "Gemini")
    traced["trace"][-1]["source"] = (assessment.get("parameter_generation") or {}).get("source", "live_provider")
    traced["trace"][-1]["upstream"] = "hazard_api"
    traced = trace_event(
        traced,
        stage="ml_inference",
        status="completed",
        title="XGBoost damage and urgency assessment",
        request={"validated_parameters": assessment.get("parameters", {})},
        response={key: value for key, value in assessment.items() if key not in {"parameters", "parameter_generation"}},
    )
    traced["trace"][-1]["provider"] = "local XGBoost model"
    traced["trace"][-1]["source"] = "live_model"
    traced["trace"][-1]["upstream"] = "parameter_generation"
    traced = trace_event(
        traced,
        stage="urgency_scoring",
        status="completed",
        title="Personalized urgency score calculated",
        request={"assessment": {"physical_damage_risk": assessment.get("physical_damage_risk"), "hazard_score": assessment.get("hazard_score"), "vulnerability_score": assessment.get("vulnerability_score")}},
        response={"breakdown": assessment.get("urgency_breakdown"), "urgency_score": assessment.get("urgency_score"), "urgency_level": assessment.get("urgency_level")},
    )
    traced["trace"][-1]["upstream"] = "ml_inference"
    return {**traced, "assessment": assessment, "silent": assessment.get("urgency_level") == "low"}
