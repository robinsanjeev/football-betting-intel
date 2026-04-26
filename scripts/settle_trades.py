"""Auto-settlement script for football betting signals.

Checks each PENDING signal in signal_history against the Kalshi API.
When a market reaches "determined" or "finalized" status, the result
field ("yes"/"no") tells us definitively whether the bet won or lost.

Usage:
    cd ~/.openclaw/workspace
    python3 -m football_intel.scripts.settle_trades [--days N] [--dry-run]
                                                    [--topic-id N] [--no-telegram]
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from football_intel.common.logging_utils import get_logger
from football_intel.ingestion.kalshi import KalshiClient
from football_intel.delivery.telegram_bot import TelegramClient

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STAKE = 10.0                      # Standard paper-trade stake in dollars
SETTLED_STATUSES = {"determined", "finalized"}
INTER_REQUEST_SLEEP = 0.5         # Seconds between Kalshi API calls

COMPETITION_CODES = {             # For reference only — not used in new approach
    "EPL": "PL",
    "Bundesliga": "BL1",
    "UCL": "CL",
}

# ---------------------------------------------------------------------------
# DB helpers
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


def _load_pending_signals(conn: sqlite3.Connection, days: int) -> List[sqlite3.Row]:
    """Return all PENDING signals generated within the last `days` days.

    Only includes signals where bet_placed = 1 (passed composite score filters).
    """
    cutoff = (dt.datetime.utcnow() - dt.timedelta(days=days)).isoformat()
    rows = conn.execute(
        """
        SELECT id, market_ticker, match_title, competition,
               bet_type, description, kalshi_implied_prob,
               entry_cents, upside_cents, event_ticker
        FROM signal_history
        WHERE outcome = 'PENDING'
          AND bet_placed = 1
          AND generated_at >= ?
        ORDER BY generated_at ASC
        """,
        (cutoff,),
    ).fetchall()
    logger.info("Found %d PENDING bet_placed signals (last %d days)", len(rows), days)
    return rows


def _parse_match_date(event_ticker, fallback_date):
    # type: (str, str) -> str
    """Extract match date from Kalshi event ticker.

    Tickers contain dates like 26APR18 meaning 2026-04-18.
    Falls back to the provided date string if parsing fails.
    """
    months = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12,
    }
    m = re.search(
        r'26(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{2})',
        event_ticker or '',
        re.IGNORECASE,
    )
    if m:
        month = months.get(m.group(1).upper(), 4)
        day = int(m.group(2))
        return "2026-{:02d}-{:02d}".format(month, day)
    return fallback_date[:10] if fallback_date else dt.date.today().isoformat()


def _update_signal(
    conn: sqlite3.Connection,
    signal_id: int,
    outcome: str,
    pnl: float,
    dry_run: bool,
) -> None:
    if dry_run:
        logger.info("[DRY-RUN] Would update signal %d → %s (pnl=%.2f)", signal_id, outcome, pnl)
        return
    conn.execute(
        "UPDATE signal_history SET outcome = ?, actual_pnl = ? WHERE id = ?",
        (outcome, pnl, signal_id),
    )
    conn.commit()
    logger.debug("Updated signal %d → %s (pnl=%.2f)", signal_id, outcome, pnl)


def _update_trades(
    conn: sqlite3.Connection,
    match_title: str,
    description: str,
    outcome: str,
    pnl: float,
    dry_run: bool,
    event_ticker: str = "",
    generated_at: str = "",
) -> int:
    """Upsert a trade row and settle it.

    Uses the match date parsed from event_ticker instead of generated_at.
    Returns count of rows affected.
    """
    match_date = _parse_match_date(event_ticker, generated_at)

    if dry_run:
        logger.info(
            "[DRY-RUN] Would upsert trade for match=%r desc=%r → %s (pnl=%.2f, date=%s)",
            match_title, description, outcome, pnl, match_date,
        )
        return 0

    # Ensure trades table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            match TEXT NOT NULL,
            side TEXT NOT NULL,
            stake REAL NOT NULL,
            odds REAL,
            result TEXT DEFAULT 'PENDING',
            pnl REAL DEFAULT 0.0
        )
    """)

    # Try to update an existing PENDING trade first
    cur = conn.execute(
        """
        UPDATE trades
        SET result = ?, pnl = ?, timestamp = ?
        WHERE result = 'PENDING'
          AND match = ?
          AND side = ?
        """,
        (outcome, pnl, match_date, match_title, description),
    )
    conn.commit()
    count = cur.rowcount

    # If no existing row, insert a new settled trade
    if count == 0:
        conn.execute(
            """
            INSERT INTO trades (timestamp, match, side, stake, odds, result, pnl)
            VALUES (?, ?, ?, ?, NULL, ?, ?)
            """,
            (match_date, match_title, description, STAKE, outcome, pnl),
        )
        conn.commit()
        count = 1
        logger.debug(
            "Inserted settled trade for match=%r desc=%r date=%s",
            match_title, description, match_date,
        )
    else:
        logger.debug(
            "Updated %d trade row(s) for match=%r desc=%r",
            count, match_title, description,
        )
    return count


# ---------------------------------------------------------------------------
# Kalshi market lookup
# ---------------------------------------------------------------------------

def _get_market(kalshi: KalshiClient, ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch a single Kalshi market by ticker.  Returns None on error."""
    try:
        data = kalshi._get(f"/markets/{ticker}")
        # The API may nest the market under a 'market' key
        return data.get("market", data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch market %s: %s", ticker, exc)
        return None


# ---------------------------------------------------------------------------
# Settlement logic
# ---------------------------------------------------------------------------

def _calculate_pnl(outcome: str, entry_cents: int, upside_cents: int) -> float:
    """Calculate PnL for a settled signal.

    WIN:  stake * (upside_cents / entry_cents)
    LOSE: -stake
    """
    if outcome == "WIN":
        if entry_cents and entry_cents > 0:
            return round(STAKE * (upside_cents / entry_cents), 2)
        # Fallback: shouldn't happen but guard against divide-by-zero
        return round(STAKE * 0.5, 2)
    return -STAKE


def settle_all(
    *,
    days: int = 7,
    dry_run: bool = False,
    topic_id: int = 31,
    send_telegram: bool = True,
) -> Dict[str, Any]:
    """Main settlement routine.

    Returns a summary dict with keys:
        settled, wins, losses, skipped, net_pnl, lines (for Telegram)
    """
    conn = _get_conn()
    kalshi = KalshiClient()

    pending = _load_pending_signals(conn, days)
    if not pending:
        logger.info("No pending signals to settle.")
        return {"settled": 0, "wins": 0, "losses": 0, "skipped": 0, "net_pnl": 0.0, "lines": []}

    settled_count = 0
    wins = 0
    losses = 0
    skipped = 0
    net_pnl = 0.0
    report_lines: List[str] = []

    for row in pending:
        signal_id    = row["id"]
        ticker       = row["market_ticker"]
        match_title  = row["match_title"]
        bet_type     = row["bet_type"]
        description  = row["description"]
        entry_cents  = row["entry_cents"]
        upside_cents = row["upside_cents"]
        event_ticker = row["event_ticker"] if "event_ticker" in row.keys() else ""

        print(f"  Checking {ticker} ({match_title} — {description})…", flush=True)

        market = _get_market(kalshi, ticker)
        time.sleep(INTER_REQUEST_SLEEP)

        if market is None:
            logger.warning("Skipping signal %d — could not fetch market %s", signal_id, ticker)
            skipped += 1
            continue

        status = (market.get("status") or "").lower()
        result = (market.get("result") or "").lower()

        logger.debug(
            "signal_id=%d ticker=%s status=%r result=%r",
            signal_id, ticker, status, result,
        )

        # Only settle when the market is fully determined
        if status not in SETTLED_STATUSES:
            logger.info(
                "Signal %d (%s) still %s — skipping", signal_id, ticker, status
            )
            skipped += 1
            continue

        if result == "yes":
            outcome = "WIN"
        elif result == "no":
            outcome = "LOSE"
        else:
            # Determined/finalized but result not populated yet — unusual, skip
            logger.warning(
                "Signal %d (%s) is %s but result=%r — skipping",
                signal_id, ticker, status, result,
            )
            skipped += 1
            continue

        pnl = _calculate_pnl(outcome, entry_cents, upside_cents)

        # Persist
        _update_signal(conn, signal_id, outcome, pnl, dry_run)
        _update_trades(
            conn, match_title, description, outcome, pnl, dry_run,
            event_ticker=event_ticker,
        )

        # Tally
        settled_count += 1
        net_pnl += pnl
        if outcome == "WIN":
            wins += 1
            emoji = "✅"
            pnl_str = f"+${pnl:.2f}"
        else:
            losses += 1
            emoji = "❌"
            pnl_str = f"-${abs(pnl):.2f}"

        line = f"{emoji} {match_title} — {description} → {outcome} ({pnl_str})"
        report_lines.append(line)
        print(f"    {line}", flush=True)

    conn.close()

    summary = {
        "settled": settled_count,
        "wins": wins,
        "losses": losses,
        "skipped": skipped,
        "net_pnl": round(net_pnl, 2),
        "lines": report_lines,
    }

    # ------------------------------------------------------------------
    # Running totals from the full signal_history table
    # ------------------------------------------------------------------
    try:
        conn2 = _get_conn()
        row = conn2.execute(
            """
            SELECT
                COUNT(*)                                    AS total_settled,
                SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS total_wins,
                SUM(actual_pnl)                             AS total_pnl
            FROM signal_history
            WHERE outcome IN ('WIN','LOSE')
            """
        ).fetchone()
        conn2.close()
        summary["total_settled"] = row[0] or 0
        summary["total_wins"]    = row[1] or 0
        summary["total_pnl"]     = round(row[2] or 0.0, 2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not compute running totals: %s", exc)
        summary["total_settled"] = 0
        summary["total_wins"]    = 0
        summary["total_pnl"]     = 0.0

    # ------------------------------------------------------------------
    # Adaptive feedback loop: update signal parameters if enough data
    # ------------------------------------------------------------------
    if not dry_run:
        try:
            from football_intel.strategy.adaptive import AdaptiveAnalyzer
            analyzer = AdaptiveAnalyzer()
            analysis = analyzer.analyze_settled_trades()
            if analysis["total_settled"] >= AdaptiveAnalyzer.MIN_SAMPLES:
                new_params = analyzer.compute_optimal_params(analysis)
                analyzer.save_params(new_params)
                logger.info("Adaptive params updated (v%d)", new_params.version)
                summary["adaptive_version"] = new_params.version
            else:
                logger.info(
                    "Adaptive: only %d/%d settled trades — warming up",
                    analysis["total_settled"],
                    AdaptiveAnalyzer.MIN_SAMPLES,
                )
                summary["adaptive_version"] = None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Adaptive feedback loop failed: %s", exc)

    # ------------------------------------------------------------------
    # Telegram report
    # ------------------------------------------------------------------
    if send_telegram and settled_count > 0:
        _send_telegram_report(summary, topic_id, dry_run)

    return summary


def _send_telegram_report(
    summary: Dict[str, Any],
    topic_id: int,
    dry_run: bool,
) -> None:
    """Build and send the settlement summary to Telegram."""
    lines = summary["lines"]
    wins  = summary["wins"]
    losses = summary["losses"]
    net_pnl = summary["net_pnl"]
    total_settled = summary.get("total_settled", 0)
    total_wins    = summary.get("total_wins", 0)
    total_pnl     = summary.get("total_pnl", 0.0)

    win_rate_pct = (
        round(total_wins / total_settled * 100, 1) if total_settled else 0.0
    )
    net_str = f"+${net_pnl:.2f}" if net_pnl >= 0 else f"-${abs(net_pnl):.2f}"
    total_pnl_str = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"

    body = "\n".join(lines)
    message = (
        f"📊 Settlement Report\n\n"
        f"{body}\n\n"
        f"Today: {wins}W / {losses}L | Net: {net_str}\n"
        f"Running total: {total_settled} trades settled, "
        f"{win_rate_pct}% win rate, {total_pnl_str} total PnL"
    )

    if dry_run:
        print("\n[DRY-RUN] Telegram message would be:\n")
        print(message)
        return

    try:
        tg = TelegramClient()
        tg.send_message(message, topic_id=topic_id)
        logger.info("Settlement report sent to Telegram topic %d", topic_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send Telegram settlement report: %s", exc)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Settle PENDING football betting signals via Kalshi market results.",
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="How many days back to look for pending signals (default: 7)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be settled without writing to the DB",
    )
    parser.add_argument(
        "--topic-id", type=int, default=31,
        help="Telegram topic/thread ID for the settlement report (default: 31)",
    )
    parser.add_argument(
        "--no-telegram", action="store_true",
        help="Skip sending the Telegram settlement report",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    print("=" * 60, flush=True)
    print("  Football Intel — Trade Settlement", flush=True)
    if args.dry_run:
        print("  ⚠️  DRY-RUN MODE — no DB changes will be made", flush=True)
    print("=" * 60, flush=True)

    summary = settle_all(
        days=args.days,
        dry_run=args.dry_run,
        topic_id=args.topic_id,
        send_telegram=not args.no_telegram,
    )

    print("\n--- Summary ---", flush=True)
    print(f"  Settled : {summary['settled']}", flush=True)
    print(f"  Wins    : {summary['wins']}", flush=True)
    print(f"  Losses  : {summary['losses']}", flush=True)
    print(f"  Skipped : {summary['skipped']}  (not yet determined)", flush=True)
    net = summary["net_pnl"]
    net_str = f"+${net:.2f}" if net >= 0 else f"-${abs(net):.2f}"
    print(f"  Net PnL : {net_str}", flush=True)

    total_settled = summary.get("total_settled", 0)
    total_pnl     = summary.get("total_pnl", 0.0)
    total_wins    = summary.get("total_wins", 0)
    win_rate = (total_wins / total_settled * 100) if total_settled else 0.0
    total_str = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"
    print(
        f"\nAll-time: {total_settled} settled | "
        f"{win_rate:.1f}% win rate | {total_str} total PnL",
        flush=True,
    )


if __name__ == "__main__":
    main()
