"""Shared state contract for the SentinelHome agent workflow."""

from __future__ import annotations

from typing import Any, TypedDict


class SentinelState(TypedDict, total=False):
    household: dict[str, Any]
    earthquake: dict[str, Any]
    assessment: dict[str, Any]
    advice: dict[str, Any]
    alert: dict[str, Any]
    confirmation_status: str
    escalation_required: bool
    completed: bool
    silent: bool
    errors: list[str]


def append_error(state: SentinelState, message: str) -> SentinelState:
    errors = list(state.get("errors", []))
    errors.append(message)
    return {**state, "errors": errors}
