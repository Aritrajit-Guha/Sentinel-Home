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

    return errors
