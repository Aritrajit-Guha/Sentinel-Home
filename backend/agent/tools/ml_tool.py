"""Inference adapter for the saved earthquake damage pipeline."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BACKEND_DIR / "ml" / "models"
MODEL_PATH = MODEL_DIR / "earthquake_damage_model.pkl"
METADATA_PATH = MODEL_DIR / "earthquake_model_metadata.json"


@lru_cache(maxsize=1)
def _load_artifacts():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Earthquake model not found: {MODEL_PATH}")
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return joblib.load(MODEL_PATH), metadata


def predict_building_damage(parameters: dict) -> dict:
    """Run one validated parameter object through the saved pipeline."""
    if not isinstance(parameters, dict):
        raise TypeError("parameters must be a dictionary")

    model, metadata = _load_artifacts()
    expected_features = metadata["input_features"]
    missing = [feature for feature in expected_features if feature not in parameters]
    if missing:
        raise ValueError(f"Missing model features: {missing}")

    model_input = pd.DataFrame([
        {feature: parameters[feature] for feature in expected_features}
    ])
    predicted_index = int(model.predict(model_input)[0])
    probability_values = model.predict_proba(model_input)[0].tolist()
    class_labels = metadata["class_labels"]

    return {
        "damage_grade": int(metadata["index_to_class"][str(predicted_index)]),
        "probabilities": {
            str(label): float(probability)
            for label, probability in zip(class_labels, probability_values)
        },
    }
