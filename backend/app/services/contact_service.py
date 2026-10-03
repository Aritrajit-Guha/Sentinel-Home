"""Household contact normalization and validation helpers."""

from __future__ import annotations

import re
from uuid import uuid4


PHONE_RE = re.compile(r"^\+?[0-9][0-9\s().-]{6,18}$")


def normalize_phone(value: str) -> str:
    return re.sub(r"\D", "", str(value or ""))


def valid_phone(value: str) -> bool:
    digits = normalize_phone(value)
    return bool(PHONE_RE.fullmatch(str(value or "").strip())) and 7 <= len(digits) <= 15


def contact_errors(payload: dict) -> list[str]:
    errors = []
    primary = payload.get("primary_contact")
    if primary is not None:
        if not isinstance(primary, dict):
            errors.append("primary_contact must be an object")
        else:
            for field in ("name", "phone"):
                if not str(primary.get(field, "")).strip():
                    errors.append(f"primary_contact.{field} is required")
            if primary.get("phone") and not valid_phone(primary["phone"]):
                errors.append("primary_contact.phone must be a valid international phone number")

    relatives = payload.get("relatives")
    if relatives is not None:
        if not isinstance(relatives, list):
            errors.append("relatives must be a list")
        else:
            seen = set()
            for index, relative in enumerate(relatives):
                prefix = f"relatives[{index}]"
                if not isinstance(relative, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                for field in ("name", "relationship", "phone"):
                    if not str(relative.get(field, "")).strip():
                        errors.append(f"{prefix}.{field} is required")
                if relative.get("phone"):
                    if not valid_phone(relative["phone"]):
                        errors.append(f"{prefix}.phone must be a valid international phone number")
                    normalized = normalize_phone(relative["phone"])
                    if normalized in seen:
                        errors.append("contact phone numbers must be unique")
                    seen.add(normalized)

            if isinstance(primary, dict) and primary.get("phone"):
                primary_phone = normalize_phone(primary["phone"])
                if primary_phone in seen:
                    errors.append("contact phone numbers must be unique")
    return errors


def prepare_contacts(payload: dict) -> dict:
    """Return stable contact records while retaining legacy fields."""
    result = dict(payload)
    primary = result.get("primary_contact")
    if primary is None and isinstance(result.get("emergency_contact"), dict):
        primary = result["emergency_contact"]
    if isinstance(primary, dict):
        result["primary_contact"] = {
            "id": primary.get("id", "primary"),
            "name": str(primary.get("name", "")).strip(),
            "phone": str(primary.get("phone", "")).strip(),
        }
        result["emergency_contact"] = dict(result["primary_contact"])

    if "relatives" in result:
        relatives = []
        for relative in result.get("relatives") or []:
            relatives.append({
                "id": relative.get("id") or str(uuid4()),
                "name": str(relative.get("name", "")).strip(),
                "relationship": str(relative.get("relationship", "")).strip(),
                "phone": str(relative.get("phone", "")).strip(),
                "receive_call": bool(relative.get("receive_call", True)),
            })
        result["relatives"] = relatives
    return result


def primary_contact(household: dict) -> dict | None:
    contact = household.get("primary_contact")
    if isinstance(contact, dict) and contact.get("phone"):
        return contact
    legacy = household.get("emergency_contact")
    if isinstance(legacy, dict) and legacy.get("phone"):
        return legacy
    if isinstance(legacy, str) and legacy.strip():
        return {"id": "primary", "name": "Primary contact", "phone": legacy.strip()}
    return None


def escalation_contacts(household: dict) -> list[dict]:
    return [
        contact for contact in household.get("relatives", [])
        if isinstance(contact, dict) and contact.get("phone") and contact.get("receive_call", True)
    ]
