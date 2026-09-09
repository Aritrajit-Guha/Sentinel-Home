# Phase 3: loads the trained ML model and scores household risk
import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../../ml/models/risk_model.pkl")
_model = None

def get_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model

def score_household(features: dict) -> float:
    model = get_model()
    # TODO: transform `features` dict into the exact column order the model expects
    prediction = model.predict_proba([list(features.values())])
    return float(prediction[0][-1])  # probability of highest damage class
