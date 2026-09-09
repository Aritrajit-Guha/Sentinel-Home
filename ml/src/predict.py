"""
Loads the trained model + encoders and exposes a single `score_building()`
function. This is what backend/app/services/scoring_service.py should
import (or reimplement as an HTTP call if you serve the model separately).
"""
import pickle
from pathlib import Path

import pandas as pd

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"

with open(MODEL_DIR / "risk_model.pkl", "rb") as f:
    _model = pickle.load(f)
with open(MODEL_DIR / "label_encoders.pkl", "rb") as f:
    _encoders = pickle.load(f)
with open(MODEL_DIR / "feature_columns.pkl", "rb") as f:
    _feature_columns = pickle.load(f)


def score_building(features: dict) -> dict:
    """
    features: dict matching the raw column names from the Nepal dataset
              (geo_level_1_id, age, foundation_type, etc.)

    Returns: {"damage_grade": int (1-3), "probabilities": [p1, p2, p3]}
    """
    df = pd.DataFrame([features])

    for col, encoder in _encoders.items():
        if col in df.columns:
            df[col] = encoder.transform(df[col])

    df = df[_feature_columns]

    pred = _model.predict(df)[0] + 1  # shift back to 1-3
    proba = _model.predict_proba(df)[0].tolist()

    return {"damage_grade": int(pred), "probabilities": proba}


if __name__ == "__main__":
    # quick manual smoke test — replace with a real building's features
    example = {
        "geo_level_1_id": 6, "geo_level_2_id": 487, "geo_level_3_id": 12198,
        "count_floors_pre_eq": 2, "age": 30, "area_percentage": 6,
        "height_percentage": 5, "land_surface_condition": "t",
        "foundation_type": "r", "roof_type": "n", "ground_floor_type": "f",
        "other_floor_type": "q", "position": "t", "plan_configuration": "d",
        "has_superstructure_adobe_mud": 1, "has_superstructure_mud_mortar_stone": 1,
        "has_superstructure_stone_flag": 0, "has_superstructure_cement_mortar_stone": 0,
        "has_superstructure_mud_mortar_brick": 0, "has_superstructure_cement_mortar_brick": 0,
        "has_superstructure_timber": 0, "has_superstructure_bamboo": 0,
        "has_superstructure_rc_non_engineered": 0, "has_superstructure_rc_engineered": 0,
        "has_superstructure_other": 0, "legal_ownership_status": "v",
        "count_families": 1, "has_secondary_use": 0, "has_secondary_use_agriculture": 0,
        "has_secondary_use_hotel": 0, "has_secondary_use_rental": 0,
        "has_secondary_use_institution": 0, "has_secondary_use_school": 0,
        "has_secondary_use_industry": 0, "has_secondary_use_health_post": 0,
        "has_secondary_use_gov_office": 0, "has_secondary_use_use_police": 0,
        "has_secondary_use_other": 0,
    }
    print(score_building(example))
