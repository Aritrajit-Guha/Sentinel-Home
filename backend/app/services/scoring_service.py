"""Building-damage inference and personalized household urgency scoring."""

from __future__ import annotations

from agent.tools.ml_tool import predict_building_damage
from agent.tools.model_parameter_tool import generate_parameters_for_household


VULNERABILITY_WEIGHTS = {
    "children": 0.10,
    "elderly": 0.15,
    "disabled": 0.20,
    "pregnant": 0.15,
    "medical": 0.20,
}


def _physical_damage_risk(damage_result: dict) -> float:
    probabilities = damage_result["probabilities"]
    expected_grade = sum(
        float(grade) * float(probability)
        for grade, probability in probabilities.items()
    )
    return max(0.0, min(1.0, (expected_grade - 1.0) / 4.0))


def _hazard_severity(earthquake: dict) -> float:
    magnitude = float(earthquake.get("magnitude") or 0.0)
    mmi = float(earthquake.get("mmi") or 0.0)
    distance = float(earthquake.get("distance_km") or 500.0)
    magnitude_score = max(0.0, min(1.0, (magnitude - 3.0) / 5.0))
    mmi_score = max(0.0, min(1.0, mmi / 10.0))
    distance_score = max(0.0, min(1.0, 1.0 - distance / 500.0))
    return 0.4 * magnitude_score + 0.4 * mmi_score + 0.2 * distance_score


def _vulnerability_score(household: dict) -> float:
    members = household.get("vulnerable_members") or []
    score = sum(VULNERABILITY_WEIGHTS.get(member, 0.0) for member in members)
    household_size = max(1, int(household.get("household_size") or 1))
    size_factor = min(0.10, max(0, household_size - 4) * 0.02)
    return min(1.0, score + size_factor)


def urgency_level_for(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def assess_household_risk(household: dict, earthquake: dict) -> dict:
    """Generate model inputs, run ML, and calculate urgency."""
    parameters = generate_parameters_for_household(household, earthquake)
    damage_result = predict_building_damage(parameters)
    physical_risk = _physical_damage_risk(damage_result)
    hazard_score = _hazard_severity(earthquake)
    vulnerability_score = _vulnerability_score(household)
    urgency_score = min(
        1.0,
        0.60 * physical_risk
        + 0.25 * hazard_score
        + 0.15 * vulnerability_score,
    )

    return {
        "parameters": parameters,
        "damage_grade": damage_result["damage_grade"],
        "damage_probabilities": damage_result["probabilities"],
        "physical_damage_risk": round(physical_risk, 4),
        "hazard_score": round(hazard_score, 4),
        "vulnerability_score": round(vulnerability_score, 4),
        "urgency_score": round(urgency_score, 4),
        "urgency_level": urgency_level_for(urgency_score),
    }
