"""Pre-match odds snapshot tracker.

Snapshots Kalshi odds at multiple points before a match to track line
movement and require edge persistence before emitting a signal.

Usage:
    from football_intel.ingestion.odds_tracker import OddsTracker

    tracker = OddsTracker()
    tracker.take_snapshot(markets)  # list of (market_ticker, kalshi_prob, model_prob)
    persists = tracker.check_edge_persistence("TICKER-123", current_edge=0.12)
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# DB path helper (mirrors the one in api/main.py)
# ---------------------------------------------------------------------------

def _get_db_path() -> str:
    return os.environ.get(
        "FOOTBALL_INTEL_DB",
        "football_intel/data/football_intel.db",
    )


def _get_conn() -> sqlite3.Connection:
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_ticker TEXT NOT NULL,
    snapshot_time TEXT NOT NULL,
    kalshi_implied_prob REAL NOT NULL,
    model_prob REAL NOT NULL,
    edge REAL NOT NULL
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_odds_snapshots_ticker
ON odds_snapshots (market_ticker);
"""


def _ensure_table(conn: sqlite3.Connection) -> None:
    """Create the odds_snapshots table if it doesn't exist."""
    conn.execute(_CREATE_TABLE_SQL)
    conn.execute(_CREATE_INDEX_SQL)
    conn.commit()


# ---------------------------------------------------------------------------
# Snapshot data model
# ---------------------------------------------------------------------------

class OddsSnapshot:
    """A single odds snapshot for a market."""

    __slots__ = ("id", "market_ticker", "snapshot_time", "kalshi_implied_prob", "model_prob", "edge")

    def __init__(
        self,
        market_ticker: str,
        snapshot_time: str,
        kalshi_implied_prob: float,
        model_prob: float,
        edge: float,
        id: Optional[int] = None,
    ) -> None:
        self.id = id
        self.market_ticker = market_ticker
        self.snapshot_time = snapshot_time
        self.kalshi_implied_prob = kalshi_implied_prob
        self.model_prob = model_prob
        self.edge = edge

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "market_ticker": self.market_ticker,
            "snapshot_time": self.snapshot_time,
            "kalshi_implied_prob": round(self.kalshi_implied_prob, 4),
            "model_prob": round(self.model_prob, 4),
            "edge": round(self.edge, 4),
        }


# ---------------------------------------------------------------------------
# Main tracker class
# ---------------------------------------------------------------------------

class OddsTracker:
    """Track Kalshi odds snapshots and check edge persistence.

    Args:
        min_persistent_snapshots: Number of prior snapshots that must show
            positive edge for the signal to be considered persistent.
            Default: 2 (current + 1 prior).
    """

    def __init__(self, min_persistent_snapshots: int = 2) -> None:
        self.min_persistent_snapshots = min_persistent_snapshots

    # ------------------------------------------------------------------
    # Snapshot creation
    # ------------------------------------------------------------------

    def take_snapshot(
        self,
        market_data: List[Tuple[str, float, float]],
    ) -> int:
        """Record a batch of odds snapshots.

        Args:
            market_data: List of (market_ticker, kalshi_implied_prob, model_prob).

        Returns:
            Number of snapshots inserted.
        """
        if not market_data:
            return 0

        now = datetime.now(tz=timezone.utc).isoformat()
        conn = _get_conn()
        try:
            _ensure_table(conn)
            rows = [
                (ticker, now, kalshi_prob, model_prob, model_prob - kalshi_prob)
                for ticker, kalshi_prob, model_prob in market_data
            ]
            conn.executemany(
                """
                INSERT INTO odds_snapshots
                    (market_ticker, snapshot_time, kalshi_implied_prob, model_prob, edge)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            count = len(rows)
            logger.info("Recorded %d odds snapshots at %s", count, now)
            return count
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Edge persistence check
    # ------------------------------------------------------------------

    def check_edge_persistence(
        self,
        market_ticker: str,
        current_edge: float,
    ) -> bool:
        """Check whether edge has persisted across snapshots.

        Returns True if:
          - The current edge is positive AND
          - At least (min_persistent_snapshots - 1) prior snapshots also
            showed positive edge.
          - If no prior snapshots exist, returns True (first-time signal).

        Args:
            market_ticker: The Kalshi market ticker.
            current_edge: The current computed edge.

        Returns:
            True if the signal should be emitted.
        """
        if current_edge <= 0:
            return False

        conn = _get_conn()
        try:
            _ensure_table(conn)
            rows = conn.execute(
                """
                SELECT edge FROM odds_snapshots
                WHERE market_ticker = ?
                ORDER BY snapshot_time DESC
                LIMIT ?
                """,
                (market_ticker, self.min_persistent_snapshots),
            ).fetchall()

            # No prior snapshots — first time seeing this market → emit signal
            if len(rows) == 0:
                return True

            # Count how many prior snapshots had positive edge
            positive_count = sum(1 for row in rows if float(row["edge"]) > 0)

            # Need at least (min_persistent_snapshots - 1) prior positive edges
            required = self.min_persistent_snapshots - 1
            return positive_count >= required

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Query helpers (for API endpoints)
    # ------------------------------------------------------------------

    def get_snapshots_for_market(self, market_ticker: str) -> List[OddsSnapshot]:
        """Return all snapshots for a specific market, ordered by time."""
        conn = _get_conn()
        try:
            _ensure_table(conn)
            rows = conn.execute(
                """
                SELECT id, market_ticker, snapshot_time, kalshi_implied_prob, model_prob, edge
                FROM odds_snapshots
                WHERE market_ticker = ?
                ORDER BY snapshot_time ASC
                """,
                (market_ticker,),
            ).fetchall()
            return [
                OddsSnapshot(
                    id=row["id"],
                    market_ticker=row["market_ticker"],
                    snapshot_time=row["snapshot_time"],
                    kalshi_implied_prob=row["kalshi_implied_prob"],
                    model_prob=row["model_prob"],
                    edge=row["edge"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_all_snapshots(self) -> List[OddsSnapshot]:
        """Return all snapshots across all markets, ordered by time descending."""
        conn = _get_conn()
        try:
            _ensure_table(conn)
            rows = conn.execute(
                """
                SELECT id, market_ticker, snapshot_time, kalshi_implied_prob, model_prob, edge
                FROM odds_snapshots
                ORDER BY snapshot_time DESC
                LIMIT 1000
                """,
            ).fetchall()
            return [
                OddsSnapshot(
                    id=row["id"],
                    market_ticker=row["market_ticker"],
                    snapshot_time=row["snapshot_time"],
                    kalshi_implied_prob=row["kalshi_implied_prob"],
                    model_prob=row["model_prob"],
                    edge=row["edge"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def get_persistence_status(self, market_ticker: str) -> Dict[str, Any]:
        """Return persistence info for a market: snapshot count, all positive, etc."""
        conn = _get_conn()
        try:
            _ensure_table(conn)
            rows = conn.execute(
                """
                SELECT edge FROM odds_snapshots
                WHERE market_ticker = ?
                ORDER BY snapshot_time DESC
                """,
                (market_ticker,),
            ).fetchall()

            total = len(rows)
            positive = sum(1 for r in rows if float(r["edge"]) > 0)
            is_persistent = total >= self.min_persistent_snapshots and positive >= self.min_persistent_snapshots
            is_new = total < self.min_persistent_snapshots

            return {
                "market_ticker": market_ticker,
                "total_snapshots": total,
                "positive_snapshots": positive,
                "is_persistent": is_persistent,
                "is_new": is_new,
            }
        finally:
            conn.close()
