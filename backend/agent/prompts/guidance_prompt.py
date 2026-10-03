"""Prompts for retrieving and generating grounded disaster guidance."""

from __future__ import annotations

import json


def build_retrieval_query(earthquake: dict, assessment: dict) -> str:
    return (
        "Official earthquake safety guidance for a household near "
        f"{earthquake.get('place', 'the affected area')}. "
        f"Magnitude {earthquake.get('magnitude')}, MMI {earthquake.get('mmi')}, "
        f"distance {earthquake.get('distance_km')} km, "
        f"predicted damage grade {assessment.get('damage_grade')}, "
        f"urgency level {assessment.get('urgency_level')}."
    )


def build_guidance_prompt(
    household: dict,
    earthquake: dict,
    assessment: dict,
    context: str,
) -> str:
    """Build a concise, source-grounded emergency instruction prompt."""

    household_context = {
        "household_size": household.get("household_size"),
        "vulnerable_members": household.get("vulnerable_members", []),
        "location": household.get("location"),
    }
    hazard_context = {
        "place": earthquake.get("place"),
        "magnitude": earthquake.get("magnitude"),
        "mmi": earthquake.get("mmi"),
        "distance_km": earthquake.get("distance_km"),
    }
    risk_context = {
        "damage_grade": assessment.get("damage_grade"),
        "physical_damage_risk": assessment.get("physical_damage_risk"),
        "urgency_score": assessment.get("urgency_score"),
        "urgency_level": assessment.get("urgency_level"),
    }
    return f"""
You are SentinelHome's emergency safety-message generator.

Write one concise, calm, actionable household instruction using only the
official retrieved guidance below and the supplied structured facts.

Rules:
- Do not invent shelters, routes, medical advice, timings, or hazard facts.
- Do not change the supplied risk or urgency values.
- Do not mention internal model implementation details.
- Prioritize immediate safety and assistance for vulnerable members.
- If the guidance does not support a specific recommendation, say to follow
  local authority instructions.
- Return plain text only, at most 500 characters.

Household:
{json.dumps(household_context, ensure_ascii=False, indent=2)}

Earthquake:
{json.dumps(hazard_context, ensure_ascii=False, indent=2)}

Assessment:
{json.dumps(risk_context, ensure_ascii=False, indent=2)}

Official retrieved guidance:
{context}
""".strip()
