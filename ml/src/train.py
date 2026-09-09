"""
Phase 3 — Baseline risk-scoring model.

Trains a classifier on the Nepal Earthquake Damage dataset to predict
`damage_grade` (1 = low, 2 = medium, 3 = high) from building/structure
features. This is the starting point for SentinelHome's personalized
urgency score: in production, building features get combined with a
household's stored profile (occupants, vulnerable members) and live
hazard data before being passed through a model like this one.

Usage:
    cd ml
    python src/train.py

Outputs:
    ml/models/risk_model.pkl        <- trained model, load this in
                                        backend/app/services/scoring_service.py
    ml/models/label_encoders.pkl    <- encoders for categorical columns,
                                        needed to transform new inputs
"""

import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load and merge the building features with their damage labels."""
    values_path = DATA_DIR / "nepal_earthquake_train_values.csv"
    labels_path = DATA_DIR / "nepal_earthquake_train_labels.csv"

    if not values_path.exists() or not labels_path.exists():
        raise FileNotFoundError(
            f"Expected data files in {DATA_DIR}. "
            "See ml/data/raw/README.md for the file list."
        )

    values = pd.read_csv(values_path)
    labels = pd.read_csv(labels_path)

    df = values.merge(labels, on="building_id")
    print(f"Loaded {len(df):,} buildings with {df.shape[1]} columns.")
    return df


def encode_categoricals(df: pd.DataFrame):
    """Label-encode the categorical (single-letter-coded) columns."""
    categorical_cols = [
        "land_surface_condition",
        "foundation_type",
        "roof_type",
        "ground_floor_type",
        "other_floor_type",
        "position",
        "plan_configuration",
        "legal_ownership_status",
    ]

    encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le

    return df, encoders


def main():
    df = load_data()
    df, encoders = encode_categoricals(df)

    # damage_grade is 1/2/3 in the raw data; shift to 0/1/2 for sklearn
    y = df["damage_grade"] - 1
    X = df.drop(columns=["building_id", "damage_grade"])

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Training RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_val)
    micro_f1 = f1_score(y_val, preds, average="micro")
    print(f"\nValidation micro F1: {micro_f1:.4f}\n")
    print(classification_report(y_val, preds, target_names=["grade 1", "grade 2", "grade 3"]))

    # Feature importance — useful for your report / to justify feature choices
    importances = pd.Series(model.feature_importances_, index=X.columns)
    print("\nTop 10 most important features:")
    print(importances.sort_values(ascending=False).head(10))

    with open(MODEL_DIR / "risk_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open(MODEL_DIR / "label_encoders.pkl", "wb") as f:
        pickle.dump(encoders, f)
    with open(MODEL_DIR / "feature_columns.pkl", "wb") as f:
        pickle.dump(list(X.columns), f)

    print(f"\nSaved model + encoders to {MODEL_DIR}/")


if __name__ == "__main__":
    main()
