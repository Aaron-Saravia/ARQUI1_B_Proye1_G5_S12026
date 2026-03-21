"""Helpers pequenos."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def safe_run(fn: Callable[[], Any], cleanup: Callable[[], Any] | None = None) -> None:
    try:
        fn()
    except KeyboardInterrupt:
        print('Saliendo...')
    finally:
        if cleanup:
            cleanup()
