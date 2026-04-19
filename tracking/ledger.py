"""Paper-trading ledger and performance metrics."""

from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class Trade:
    id: int
    timestamp: dt.datetime
    match: str
    side: str
    stake: float
    odds: float
    result: str  # "WIN", "LOSE", or "PENDING"
    pnl: float


class Ledger:
    def __init__(self) -> None:
        cfg = load_config().storage
        self.db_path = Path(cfg.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    match TEXT NOT NULL,
                    side TEXT NOT NULL,
                    stake REAL NOT NULL,
                    odds REAL NOT NULL,
                    result TEXT NOT NULL DEFAULT 'PENDING',
                    pnl REAL NOT NULL DEFAULT 0.0
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def log_trade(self, match: str, side: str, stake: float, odds: float) -> None:
        ts = dt.datetime.utcnow().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO trades (timestamp, match, side, stake, odds) VALUES (?, ?, ?, ?, ?)",
                (ts, match, side, stake, odds),
            )
            conn.commit()
        finally:
            conn.close()

    def settle_trade(self, trade_id: int, result: str, pnl: float) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE trades SET result = ?, pnl = ? WHERE id = ?",
                (result, pnl, trade_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_trades(self) -> List[Trade]:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                "SELECT id, timestamp, match, side, stake, odds, result, pnl FROM trades ORDER BY id DESC"
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        trades: List[Trade] = []
        for row in rows:
            trades.append(
                Trade(
                    id=row[0],
                    timestamp=dt.datetime.fromisoformat(row[1]),
                    match=row[2],
                    side=row[3],
                    stake=row[4],
                    odds=row[5],
                    result=row[6],
                    pnl=row[7],
                )
            )
        return trades

    # --- Metrics ---------------------------------------------------------

    def metrics(self) -> dict:
        trades = self.list_trades()
        if not trades:
            return {"roi": 0.0, "max_drawdown": 0.0, "win_rate": 0.0}

        total_staked = sum(t.stake for t in trades)
        total_pnl = sum(t.pnl for t in trades)

        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        wins = 0
        settled = 0

        for t in trades[::-1]:  # oldest to newest
            if t.result != "PENDING":
                settled += 1
                if t.result == "WIN":
                    wins += 1
            equity += t.pnl
            peak = max(peak, equity)
            max_dd = min(max_dd, equity - peak)

        roi = (total_pnl / total_staked) if total_staked > 0 else 0.0
        win_rate = (wins / settled) if settled > 0 else 0.0

        return {
            "roi": roi,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
        }
