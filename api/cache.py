"""Simple in-memory signal cache with TTL."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, List, Optional


class SignalCache:
    """In-memory cache for generated betting signals.

    Stores the last computed signals list and the UTC timestamp they were
    generated.  After `ttl_seconds` seconds, `is_stale()` returns True and
    callers should regenerate the signals.
    """

    def __init__(self, ttl_seconds: int = 900) -> None:  # 15 min
        self._signals: Optional[List[Any]] = None
        self._generated_at: Optional[datetime] = None
        self._ttl = ttl_seconds
        self._set_time: Optional[float] = None  # monotonic clock at set-time

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self) -> Optional[List[Any]]:
        """Return cached signals, or None if cache is empty / stale."""
        if self.is_stale():
            return None
        return self._signals

    def set(self, signals: List[Any], generated_at: datetime) -> None:
        """Store signals with the given generation timestamp."""
        self._signals = signals
        self._generated_at = generated_at
        self._set_time = time.monotonic()

    def is_stale(self) -> bool:
        """Return True if the cache has never been populated or has expired."""
        if self._signals is None or self._set_time is None:
            return True
        elapsed = time.monotonic() - self._set_time
        return elapsed >= self._ttl

    @property
    def generated_at(self) -> Optional[datetime]:
        """UTC datetime when the cached signals were generated."""
        return self._generated_at

    def clear(self) -> None:
        """Invalidate the cache immediately."""
        self._signals = None
        self._generated_at = None
        self._set_time = None
