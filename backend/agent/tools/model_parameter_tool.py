"""Generate and validate earthquake-model parameters with Gemini."""

from __future__ import annotations

from agent.prompts.parameter_prompt import build_parameter_prompt
from agent.tools.llm_client import generate_model_parameters
from agent.validation.model_input_validator import validate_model_parameters


def generate_parameters_for_household(
    household: dict,
    earthquake: dict,
) -> dict:
    """Convert household and earthquake data into validated model inputs."""

    prompt = build_parameter_prompt(
        household=household,
        earthquake=earthquake,
    )
    candidate = generate_model_parameters(prompt)
    return validate_model_parameters(candidate)
