"""Prompt builder for generating earthquake model parameters."""

from __future__ import annotations

import json


MODEL_FEATURES = [
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
    "has_superstructure_adobe_mud",
    "has_superstructure_mud_mortar_stone",
    "has_superstructure_stone_flag",
    "has_superstructure_cement_mortar_stone",
    "has_superstructure_mud_mortar_brick",
    "has_superstructure_cement_mortar_brick",
    "has_superstructure_timber",
    "has_superstructure_bamboo",
    "has_superstructure_rc_non_engineered",
    "has_superstructure_rc_engineered",
    "has_superstructure_other",
    "magnitude",
    "epicentral_distance_km",
    "hypocentral_distance_km",
    "mmi",
]


def build_parameter_prompt(household: dict, earthquake: dict) -> str:
    """Build the prompt used to generate the ML model input parameters."""

    household_data = {
        "building_type": household.get("building_type"),
        "location": household.get("location"),
        "latitude": household.get("latitude"),
        "longitude": household.get("longitude"),
        "count_floors_pre_eq": household.get("count_floors_pre_eq"),
        "age_building": household.get("age_building"),
        "plinth_area_sq_ft": household.get("plinth_area_sq_ft"),
        "height_ft_pre_eq": household.get("height_ft_pre_eq"),
        "land_surface_condition": household.get("land_surface_condition"),
        "foundation_type": household.get("foundation_type"),
        "roof_type": household.get("roof_type"),
        "ground_floor_type": household.get("ground_floor_type"),
        "other_floor_type": household.get("other_floor_type"),
        "position": household.get("position"),
        "plan_configuration": household.get("plan_configuration"),
    }

    earthquake_data = {
        "event_id": earthquake.get("id"),
        "magnitude": earthquake.get("magnitude"),
        "mmi": earthquake.get("mmi"),
        "depth_km": earthquake.get("depth_km"),
        "latitude": earthquake.get("latitude"),
        "longitude": earthquake.get("longitude"),
        "epicentral_distance_km": earthquake.get("distance_km"),
        "hypocentral_distance_km": earthquake.get("hypocentral_distance_km"),
        "place": earthquake.get("place"),
        "time": earthquake.get("time"),
    }

    return f"""
You generate input parameters for the SentinelHome earthquake building-damage
classification model.

Convert the supplied household/building information and earthquake information
into the model's required input fields.

Do not calculate damage_grade, physical risk, urgency_score, or risk_level.
Do not generate safety advice.
Do not invent structural facts that are not supported by the supplied data.
If a value is unavailable, return null. The backend validator will decide
whether a controlled default can be used.

The earthquake distance values supplied by the backend are authoritative.
Do not recalculate or modify them.

Required output fields:
{json.dumps(MODEL_FEATURES, indent=2)}

Rules:
1. Return exactly one JSON object with no Markdown or code fences.
2. Include every required output field, even when its value is null.
3. Numeric fields must contain numbers or null.
4. Binary has_superstructure_* fields must contain only 0, 1, or null.
5. Set a superstructure field to 1 only when supported by the supplied data.
6. Set unrelated superstructure fields to 0 when the main material is known.
7. Use model-compatible categorical values.
8. Use "Not applicable" for other_floor_type when appropriate.
9. Do not use post-earthquake fields or damage observations.
10. Do not use household vulnerability to change building damage parameters.

Household and building information:
{json.dumps(household_data, indent=2, ensure_ascii=False)}

Earthquake information:
{json.dumps(earthquake_data, indent=2, ensure_ascii=False)}

Return only the JSON object.
""".strip()
