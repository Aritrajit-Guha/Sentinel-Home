# """Generate and validate earthquake-model parameters with Gemini."""

# from __future__ import annotations

# from agent.prompts.parameter_prompt import build_parameter_prompt
# from agent.tools.llm_client import generate_model_parameters
# from agent.validation.model_input_validator import validate_model_parameters


# def generate_parameters_for_household(
#     household: dict,
#     earthquake: dict,
# ) -> dict:
#     """Convert household and earthquake data into validated model inputs."""

#     prompt = build_parameter_prompt(
#         household=household,
#         earthquake=earthquake,
#     )
#     candidate = generate_model_parameters(prompt)
#     return validate_model_parameters(candidate)
"""Generate and validate earthquake-model parameters with Gemini."""

from __future__ import annotations

from agent.prompts.parameter_prompt import build_parameter_prompt
from agent.tools.llm_client import generate_model_parameters
from agent.validation.model_input_validator import (
    DEFAULT_MODEL_VALUES,
    superstructure_flags_from_materials,
    validate_model_parameters,
)


# Fields a household can supply directly at registration (see
# app/models/household.py). When present, these are known facts, not
# guesses -- they always override whatever Gemini returns for the same
# field, rather than merely being offered to Gemini as context it might or
# might not copy back faithfully.
KNOWN_BUILDING_FIELDS = (
    "count_floors_pre_eq",
    "age_building",
    "plinth_area_sq_ft",
    "height_ft_pre_eq",
    "land_surface_condition",
    "foundation_type",
    "roof_type",
    "ground_floor_type",
    "other_floor_type",
    "position",
    "plan_configuration",
)


def _fallback_parameters(household: dict, earthquake: dict) -> dict:
    """Build validated model inputs without an LLM call.

    Household registration values and normalized USGS values are deterministic
    facts.  The remaining model columns use the schema's explicit defaults.
    This keeps an upstream Gemini outage from suppressing a safety assessment;
    it does not alter the normal LLM path when Gemini is available.
    """

    candidate = dict(DEFAULT_MODEL_VALUES)
    for field in KNOWN_BUILDING_FIELDS:
        value = household.get(field)
        if value not in (None, ""):
            candidate[field] = value

    candidate.update({
        "magnitude": earthquake.get("magnitude", candidate["magnitude"]),
        "epicentral_distance_km": earthquake.get(
            "distance_km", candidate["epicentral_distance_km"]
        ),
        "hypocentral_distance_km": earthquake.get(
            "hypocentral_distance_km", candidate["hypocentral_distance_km"]
        ),
        "mmi": earthquake.get("mmi", candidate["mmi"]),
    })
    candidate.update(
        superstructure_flags_from_materials(household.get("superstructure_materials"))
    )
    return validate_model_parameters(candidate)


def generate_parameters_for_household(
    household: dict,
    earthquake: dict,
    *,
    return_metadata: bool = False,
) -> dict:
    """Convert household and earthquake data into validated model inputs."""

    prompt = build_parameter_prompt(
        household=household,
        earthquake=earthquake,
    )
    metadata = {"provider": "Gemini", "source": "live_provider", "retries": 0}
    try:
        candidate = generate_model_parameters(prompt)
    except Exception as exc:
        metadata = {"provider": "deterministic fallback", "source": "fallback", "error": str(exc)}
        result = _fallback_parameters(household, earthquake)
        return (result, metadata) if return_metadata else result

    # Known household-provided values are ground truth: they always win
    # over Gemini's guess. Gemini is only meant to fill in what the
    # household did NOT provide.
    for field in KNOWN_BUILDING_FIELDS:
        value = household.get(field)
        if value not in (None, ""):
            candidate[field] = value

    if household.get("superstructure_materials") is not None:
        candidate.update(
            superstructure_flags_from_materials(household["superstructure_materials"])
        )

    result = validate_model_parameters(candidate)
    return (result, metadata) if return_metadata else result
