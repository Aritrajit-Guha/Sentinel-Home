"""Gemini LLM client for SentinelHome model-parameter generation."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.validation.model_input_validator import EarthquakeModelParameters


load_dotenv(override=True)


class LLMConfigurationError(RuntimeError):
    """Raised when the Gemini client is not configured correctly."""


@lru_cache(maxsize=1)
def get_llm() -> ChatGoogleGenerativeAI:
    """Create and cache one Gemini client instance."""

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise LLMConfigurationError(
            "GEMINI_API_KEY or GOOGLE_API_KEY is missing"
        )

    model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
        max_retries=2,
        timeout=60,
    )


@lru_cache(maxsize=1)
def get_structured_llm():
    """Return Gemini configured for the earthquake parameter schema."""

    return get_llm().with_structured_output(
        EarthquakeModelParameters,
        method="json_schema",
    )


def generate_model_parameters(prompt: str) -> dict:
    """Generate structured earthquake-model parameters from a prompt."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    try:
        result = get_structured_llm().invoke(prompt)
    except Exception as exc:
        raise RuntimeError(
            f"Gemini parameter generation failed: {exc}"
        ) from exc

    if isinstance(result, EarthquakeModelParameters):
        return result.model_dump()
    if isinstance(result, dict):
        return result

    raise RuntimeError(
        "Gemini returned an unexpected structured-output type"
    )
