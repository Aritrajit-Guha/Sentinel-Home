# """Input validation for household registration.

# This intentionally uses plain Python dictionaries so beginners can follow the
# Flask request -> validation -> response flow without a second web framework.
# """


# REQUIRED_FIELDS = (
#     "location",
#     "latitude",
#     "longitude",
#     "building_type",
#     "household_size",
#     "emergency_contact",
# )


# ALLOWED_VULNERABLE_MEMBERS = {
#     "children",
#     "elderly",
#     "disabled",
#     "pregnant",
#     "medical",
# }


# def validate_household(payload, *, partial=False):
#     errors = []
#     if not isinstance(payload, dict):
#         return ["request body must be a JSON object"]

#     if not partial:
#         for field in REQUIRED_FIELDS:
#             if field not in payload or payload[field] in (None, ""):
#                 errors.append(f"{field} is required")

#     for field in ("latitude", "longitude"):
#         if field in payload:
#             try:
#                 float(payload[field])
#             except (TypeError, ValueError):
#                 errors.append(f"{field} must be a number")

#     if "household_size" in payload:
#         try:
#             if int(payload["household_size"]) < 1:
#                 errors.append("household_size must be at least 1")
#         except (TypeError, ValueError):
#             errors.append("household_size must be an integer")

#     if "latitude" in payload:
#         try:
#             latitude = float(payload["latitude"])
#             if not -90 <= latitude <= 90:
#                 errors.append("latitude must be between -90 and 90")
#         except (TypeError, ValueError):
#             pass

#     if "longitude" in payload:
#         try:
#             longitude = float(payload["longitude"])
#             if not -180 <= longitude <= 180:
#                 errors.append("longitude must be between -180 and 180")
#         except (TypeError, ValueError):
#             pass

#     if "vulnerable_members" in payload:
#         members = payload["vulnerable_members"]
#         if not isinstance(members, list):
#             errors.append("vulnerable_members must be a list")
#         else:
#             unknown = [member for member in members if member not in ALLOWED_VULNERABLE_MEMBERS]
#             if unknown:
#                 errors.append(
#                     "vulnerable_members contains unsupported values: "
#                     + ", ".join(str(member) for member in unknown)
#                 )

#     return errors


"""Input validation for household registration.

This intentionally uses plain Python dictionaries so beginners can follow the
Flask request -> validation -> response flow without a second web framework.
"""


REQUIRED_FIELDS = (
    "location",
    "latitude",
    "longitude",
    "building_type",
    "household_size",
    "emergency_contact",
)


ALLOWED_VULNERABLE_MEMBERS = {
    "children",
    "elderly",
    "disabled",
    "pregnant",
    "medical",
}


# ---------------------------------------------------------------------------
# Building-information fields
#
# These map directly onto the pre-earthquake structural inputs the saved
# XGBoost model (earthquake_damage_model.pkl) expects. They are optional at
# registration -- Gemini fills in anything left blank, with fallback values
# behind that -- but whatever the household DOES provide is validated here so
# it reaches the model as real signal instead of a guess.
#
# Category values are pulled directly from the OneHotEncoder fitted inside
# the saved model pipeline, so they will always match what the model was
# trained on.
# ---------------------------------------------------------------------------

"""Input validation for household registration.

This intentionally uses plain Python dictionaries so beginners can follow the
Flask request -> validation -> response flow without a second web framework.
"""

from agent.validation.model_input_validator import (
    MODEL_CATEGORICAL_VALUES as BUILDING_CATEGORICAL_FIELDS,
    SUPERSTRUCTURE_COLUMNS,
)


REQUIRED_FIELDS = (
    "location",
    "latitude",
    "longitude",
    "building_type",
    "household_size",
    "emergency_contact",
)


ALLOWED_VULNERABLE_MEMBERS = {
    "children",
    "elderly",
    "disabled",
    "pregnant",
    "medical",
}


# ---------------------------------------------------------------------------
# Building-information fields
#
# These map directly onto the pre-earthquake structural inputs the saved
# XGBoost model (earthquake_damage_model.pkl) expects. They are optional at
# registration -- Gemini fills in anything left blank, with fallback values
# behind that -- but whatever the household DOES provide is validated here so
# it reaches the model as real signal instead of a guess.
#
# BUILDING_CATEGORICAL_FIELDS and SUPERSTRUCTURE_COLUMNS are imported from
# agent/validation/model_input_validator.py rather than retyped here. That
# file is the single source of truth for the model's trained categories (read
# directly from the saved model's fitted OneHotEncoder), and it's also what
# constrains Gemini's output. Importing it means this registration form and
# the Gemini/model schema can never drift out of sync with each other.
# ---------------------------------------------------------------------------

# household-facing keys -> the has_superstructure_* column the model expects.
# Exposed as a single multi-select list (like vulnerable_members) since a
# building can have more than one construction material.
SUPERSTRUCTURE_MATERIAL_TO_COLUMN = {
    column.removeprefix("has_superstructure_"): column
    for column in SUPERSTRUCTURE_COLUMNS
}
ALLOWED_SUPERSTRUCTURE_MATERIALS = set(SUPERSTRUCTURE_MATERIAL_TO_COLUMN)

# (field, minimum, maximum) -- generous real-world bounds, not dataset bounds,
# so we reject obvious typos/garbage without rejecting unusual-but-real
# buildings. Deliberately tighter than the ge/le bounds in
# model_input_validator.py's EarthquakeModelParameters: that schema is a
# safety net for LLM output and stays permissive, while this is a UX sanity
# check on direct human input and can afford to be stricter.
BUILDING_NUMERIC_FIELDS = (
    ("count_floors_pre_eq", 1, 15),
    ("age_building", 0, 200),
    ("plinth_area_sq_ft", 1, 50000),
    ("height_ft_pre_eq", 1, 300),
)


def _validate_building_fields(payload, errors):
    for field, choices in BUILDING_CATEGORICAL_FIELDS.items():
        if field not in payload:
            continue
        value = payload[field]
        if value in (None, ""):
            continue
        if value not in choices:
            errors.append(
                f"{field} must be one of: " + ", ".join(choices)
            )

    for field, minimum, maximum in BUILDING_NUMERIC_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if value in (None, ""):
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            errors.append(f"{field} must be a number")
            continue
        if not minimum <= numeric_value <= maximum:
            errors.append(f"{field} must be between {minimum} and {maximum}")

    if "superstructure_materials" in payload:
        materials = payload["superstructure_materials"]
        if materials in (None, ""):
            pass
        elif not isinstance(materials, list):
            errors.append("superstructure_materials must be a list")
        else:
            unknown = [
                material for material in materials
                if material not in ALLOWED_SUPERSTRUCTURE_MATERIALS
            ]
            if unknown:
                errors.append(
                    "superstructure_materials contains unsupported values: "
                    + ", ".join(str(material) for material in unknown)
                )


def validate_household(payload, *, partial=False):
    errors = []
    if not isinstance(payload, dict):
        return ["request body must be a JSON object"]

    if not partial:
        for field in REQUIRED_FIELDS:
            if field not in payload or payload[field] in (None, ""):
                errors.append(f"{field} is required")

    for field in ("latitude", "longitude"):
        if field in payload:
            try:
                float(payload[field])
            except (TypeError, ValueError):
                errors.append(f"{field} must be a number")

    if "household_size" in payload:
        try:
            if int(payload["household_size"]) < 1:
                errors.append("household_size must be at least 1")
        except (TypeError, ValueError):
            errors.append("household_size must be an integer")

    if "latitude" in payload:
        try:
            latitude = float(payload["latitude"])
            if not -90 <= latitude <= 90:
                errors.append("latitude must be between -90 and 90")
        except (TypeError, ValueError):
            pass

    if "longitude" in payload:
        try:
            longitude = float(payload["longitude"])
            if not -180 <= longitude <= 180:
                errors.append("longitude must be between -180 and 180")
        except (TypeError, ValueError):
            pass

    if "vulnerable_members" in payload:
        members = payload["vulnerable_members"]
        if not isinstance(members, list):
            errors.append("vulnerable_members must be a list")
        else:
            unknown = [member for member in members if member not in ALLOWED_VULNERABLE_MEMBERS]
            if unknown:
                errors.append(
                    "vulnerable_members contains unsupported values: "
                    + ", ".join(str(member) for member in unknown)
                )

    _validate_building_fields(payload, errors)

    return errors