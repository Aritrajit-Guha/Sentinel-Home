"""Shared state contract for the SentinelHome agent workflow."""

from __future__ import annotations

from typing import Any, TypedDict
from datetime import datetime, timezone
from uuid import uuid4


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
    trace: list[dict[str, Any]]
    _trace_callback: Any
    simulation: bool


def trace_event(
    state: SentinelState,
    *,
    stage: str,
    status: str,
    title: str,
    detail: str | None = None,
    request: Any = None,
    response: Any = None,
    error: str | None = None,
) -> SentinelState:
    """Append a safe, JSON-serializable event for the internal dev console."""

    events = list(state.get("trace", []))
    event = {
        "event_id": str(uuid4()),
        "stage": stage,
        "status": status,
        "title": title,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "live",
    }
    if detail is not None:
        event["detail"] = detail
    if request is not None:
        event["request"] = request
    if response is not None:
        event["response"] = response
    if error is not None:
        event["error"] = error
    events.append(event)
    callback = state.get("_trace_callback")
    if callable(callback):
        callback(event)
    return {**state, "trace": events}


def append_error(state: SentinelState, message: str) -> SentinelState:
    errors = list(state.get("errors", []))
    errors.append(message)
    return {**state, "errors": errors}
