"""Schema and validation for the earthquake model input contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


MODEL_METADATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "ml"
    / "models"
    / "earthquake_model_metadata.json"
)


# Controlled fallbacks are used only when the user/LLM cannot provide a field.
# They keep the saved preprocessing pipeline from receiving null model inputs.
DEFAULT_MODEL_VALUES = {
    "count_floors_pre_eq": 1,
    "age_building": 10.0,
    "plinth_area_sq_ft": 400.0,
    "height_ft_pre_eq": 10.0,
    "land_surface_condition": "Flat",
    "foundation_type": "Cement-Stone/Brick",
    "roof_type": "Bamboo/Timber-Light roof",
    "ground_floor_type": "Brick/Stone",
    "other_floor_type": "Not applicable",
    "position": "Not attached",
    "plan_configuration": "Rectangular",
    "has_superstructure_adobe_mud": 0,
    "has_superstructure_mud_mortar_stone": 0,
    "has_superstructure_stone_flag": 0,
    "has_superstructure_cement_mortar_stone": 0,
    "has_superstructure_mud_mortar_brick": 0,
    "has_superstructure_cement_mortar_brick": 0,
    "has_superstructure_timber": 0,
    "has_superstructure_bamboo": 0,
    "has_superstructure_rc_non_engineered": 0,
    "has_superstructure_rc_engineered": 0,
    "has_superstructure_other": 0,
    "magnitude": 0.0,
    "epicentral_distance_km": 0.0,
    "hypocentral_distance_km": 0.0,
    "mmi": 0.0,
}


class EarthquakeModelParameters(BaseModel):
    """The 26 fields expected by the saved earthquake model pipeline."""

    model_config = ConfigDict(extra="forbid")

    count_floors_pre_eq: Optional[int] = Field(default=None, ge=1, le=100)
    age_building: Optional[float] = Field(default=None, ge=0, le=300)
    plinth_area_sq_ft: Optional[float] = Field(default=None, gt=0, le=1_000_000)
    height_ft_pre_eq: Optional[float] = Field(default=None, gt=0, le=2_000)

    land_surface_condition: Optional[str] = None
    foundation_type: Optional[str] = None
    roof_type: Optional[str] = None
    ground_floor_type: Optional[str] = None
    other_floor_type: Optional[str] = None
    position: Optional[str] = None
    plan_configuration: Optional[str] = None

    has_superstructure_adobe_mud: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_mud_mortar_stone: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_stone_flag: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_cement_mortar_stone: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_mud_mortar_brick: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_cement_mortar_brick: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_timber: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_bamboo: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_rc_non_engineered: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_rc_engineered: Optional[int] = Field(default=None, ge=0, le=1)
    has_superstructure_other: Optional[int] = Field(default=None, ge=0, le=1)

    magnitude: Optional[float] = Field(default=None, ge=0, le=10)
    epicentral_distance_km: Optional[float] = Field(default=None, ge=0)
    hypocentral_distance_km: Optional[float] = Field(default=None, ge=0)
    mmi: Optional[float] = Field(default=None, ge=0, le=12)

    @field_validator(
        "land_surface_condition",
        "foundation_type",
        "roof_type",
        "ground_floor_type",
        "other_floor_type",
        "position",
        "plan_configuration",
    )
    @classmethod
    def category_must_not_be_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("categorical model values must not be empty")
        return value


def expected_model_features() -> list[str]:
    """Read the feature order from the saved model metadata."""

    metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8"))
    return list(metadata["input_features"])


def validate_model_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate and return model parameters in metadata-defined order."""

    if not isinstance(parameters, dict):
        raise TypeError("model parameters must be a dictionary")

    expected = expected_model_features()
    missing = [feature for feature in expected if feature not in parameters]
    if missing:
        raise ValueError(f"Input is missing model features: {missing}")

    validated = EarthquakeModelParameters.model_validate(parameters)
    values = validated.model_dump()

    for feature in expected:
        if values[feature] is None:
            values[feature] = DEFAULT_MODEL_VALUES[feature]

    return {feature: values[feature] for feature in expected}
