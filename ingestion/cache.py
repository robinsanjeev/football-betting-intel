"""Simple caching layer using SQLite for match and market data.

We cache snapshots for a configurable TTL to avoid slamming upstream APIs.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    key: str
    payload: Dict[str, Any]
    created_at: dt.datetime


class Cache:
    def __init__(self) -> None:
        cfg = load_config().storage
        self.db_path = Path(cfg.db_path)
        self.ttl_hours = cfg.cache_ttl_hours
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _now(self) -> dt.datetime:
        return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)

    def put(self, key: str, payload: Dict[str, Any]) -> None:
        created_at = self._now().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "REPLACE INTO cache (key, payload, created_at) VALUES (?, ?, ?)",
                (key, json.dumps(payload), created_at),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, key: str) -> Optional[CacheEntry]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                "SELECT payload, created_at FROM cache WHERE key = ?", (key,)
            )
            row = cur.fetchone()
        finally:
            conn.close()

        if not row:
            return None

        payload_s, created_at_s = row
        created_at = dt.datetime.fromisoformat(created_at_s)
        age = self._now() - created_at.replace(tzinfo=dt.timezone.utc)
        if age > dt.timedelta(hours=self.ttl_hours):
            logger.info("Cache entry %s expired (age=%s)", key, age)
            return None

        return CacheEntry(key=key, payload=json.loads(payload_s), created_at=created_at)

    def get_many(self, keys: Iterable[str]) -> List[CacheEntry]:
        entries: List[CacheEntry] = []
        for key in keys:
            entry = self.get(key)
            if entry is not None:
                entries.append(entry)
        return entries
