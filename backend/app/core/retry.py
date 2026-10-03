"""Small bounded retry helper for transient provider failures."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_call(operation: Callable[[], T], *, attempts: int = 3, base_delay: float = 0.4) -> T:
    """Run an operation with short exponential backoff, then re-raise."""

    last_error = None
    for attempt in range(max(1, attempts)):
        try:
            return operation()
        except Exception as exc:  # provider SDKs expose different exception types
            last_error = exc
            if attempt == attempts - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
    raise last_error  # pragma: no cover
