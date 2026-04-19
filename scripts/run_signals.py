"""Standalone runner for the calibrated Poisson betting signal pipeline.

Run with:
    cd ~/.openclaw/workspace
    python3 -m football_intel.scripts.run_signals [--no-cache] [--min-edge 0.05]

Steps:
    1. Load/fetch historical match results (with 24h cache)
    2. Calibrate the Poisson model
    3. Fetch current Kalshi soccer markets
    4. Generate positive-edge betting signals
    5. Print a formatted table of signals, sorted by EV
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import List

from football_intel.delivery.telegram_bot import TelegramClient
from football_intel.ingestion.kalshi_soccer import KalshiSoccerClient, SoccerMatch
from football_intel.models.calibrated_poisson import CalibratedPoissonModel
from football_intel.models.historical_data import load_historical_results
from football_intel.strategy.signal_generator import BettingSignal, SignalGenerator
from football_intel.tracking.ledger import Ledger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Football Intel — Calibrated Poisson signal runner"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force re-fetch of historical data (ignore 24h cache)",
    )
    parser.add_argument(
        "--min-edge",
        type=float,
        default=0.05,
        help="Minimum edge (model_prob - kalshi_prob) to show a signal (default: 0.05)",
    )
    parser.add_argument(
        "--competitions",
        nargs="*",
        default=["PL", "BL1", "CL"],
        help="Competition codes to include (default: PL BL1 CL)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=30,
        help="Show top N signals (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        default=False,
        help="Send top-3 signals via Telegram and log them to the ledger",
    )
    parser.add_argument(
        "--topic-id",
        type=int,
        default=None,
        help="Telegram forum topic ID to send signals to (e.g., 31 for Betting topic)",
    )
    return parser.parse_args()


def _print_signals(signals: List[BettingSignal], top_n: int = 30) -> None:
    """Print a formatted table of betting signals."""
    if not signals:
        print("\n  ✗ No positive-edge signals found.\n")
        return

    signals_to_show = signals[:top_n]

    print(f"\n{'=' * 130}")
    print(
        f"  {'Match':<28} {'Comp':<12} {'Type':<12} "
        f"{'Model%':>8} {'Kalshi%':>8} {'Edge':>8} {'EV/$':>8} "
        f"{'Conf':<8}  Description"
    )
    print(f"{'=' * 130}")

    for s in signals_to_show:
        match_truncated = s.match_title[:28] if len(s.match_title) > 28 else s.match_title
        print(
            f"  {match_truncated:<28} {s.competition:<12} {s.bet_type:<12} "
            f"{s.model_prob:>8.1%} {s.kalshi_implied_prob:>8.1%} "
            f"{s.edge:>8.3f} {s.ev_per_dollar:>8.4f} "
            f"{s.confidence:<8}  {s.description}"
        )
        print(f"  {'':>28} {'':>12} {'':>12} {'':>8} {'':>8} {'':>8} {'':>8} {'':>8}  🔗 {s.kalshi_url}")

    print(f"{'=' * 130}")
    print(f"\n  Showing {len(signals_to_show)} of {len(signals)} total signal(s) with edge ≥ {signals[0].edge:.1%} min\n")


def main() -> int:
    """Run the full signal pipeline.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    print("\n" + "=" * 70)
    print("  ⚽  Football Intel — Calibrated Poisson Signal Runner")
    print("=" * 70)

    # ── Step 1: Historical data ──────────────────────────────────────────
    print(f"\n[1/4] Loading historical results (competitions: {', '.join(args.competitions)})…")
    try:
        results = load_historical_results(
            competition_codes=args.competitions,
            use_cache=not args.no_cache,
        )
        print(f"      ✓ {len(results)} historical matches loaded")
        if not results:
            print("      ✗ No historical data available — model will use league defaults.")
    except Exception as exc:
        print(f"      ✗ Failed to load historical data: {exc}")
        return 1

    # ── Step 2: Calibrate model ──────────────────────────────────────────
    print("\n[2/4] Calibrating Poisson model…")
    model = CalibratedPoissonModel()
    model.calibrate(results)
    for comp, stats in sorted(model.league_stats.items()):
        n_teams = len(stats.team_strengths)
        print(
            f"      {comp:>12}: {n_teams:>3} teams | "
            f"avg home goals: {stats.avg_home_goals:.2f} | "
            f"avg away goals: {stats.avg_away_goals:.2f}"
        )
    if not model.league_stats:
        print("      ⚠  No competitions calibrated — predictions will use defaults.")

    # ── Step 3: Fetch Kalshi markets ─────────────────────────────────────
    print("\n[3/4] Fetching Kalshi soccer markets…")
    try:
        client = KalshiSoccerClient()
        matches: List[SoccerMatch] = client.fetch_match_markets()
        print(f"      ✓ {len(matches)} match(es) found")
        if not matches:
            print("      No upcoming matches on Kalshi. Nothing to analyse.")
            return 0
        for m in matches[:5]:
            kickoff = m.kickoff_utc.strftime("%Y-%m-%d %H:%M UTC") if m.kickoff_utc else "TBD"
            print(f"        [{m.competition}] {m.home_team} vs {m.away_team} — {kickoff}")
        if len(matches) > 5:
            print(f"        … and {len(matches) - 5} more")
    except Exception as exc:
        print(f"      ✗ Failed to fetch Kalshi markets: {exc}")
        return 1

    # ── Step 4: Generate signals ─────────────────────────────────────────
    print(f"\n[4/4] Generating signals (min edge: {args.min_edge:.0%})…")
    generator = SignalGenerator(model)
    signals = generator.generate_signals(matches, min_edge=args.min_edge)
    print(f"      ✓ {len(signals)} signal(s) with edge ≥ {args.min_edge:.0%}")

    # ── Print results ────────────────────────────────────────────────────
    _print_signals(signals, top_n=args.top)

    # ── Record all signals to signal_history ─────────────────────────────
    if signals:
        print(f"\n[History] Recording {len(signals)} signal(s) to signal_history…")
        try:
            import os
            import sqlite3
            from datetime import datetime, timezone

            db_path = os.environ.get(
                "FOOTBALL_INTEL_DB",
                "football_intel/data/football_intel.db",
            )
            conn = sqlite3.connect(db_path)
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generated_at TEXT NOT NULL,
                    event_ticker TEXT NOT NULL,
                    market_ticker TEXT NOT NULL UNIQUE,
                    match_title TEXT NOT NULL,
                    competition TEXT NOT NULL,
                    bet_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    model_prob REAL NOT NULL,
                    kalshi_implied_prob REAL NOT NULL,
                    edge REAL NOT NULL,
                    confidence TEXT NOT NULL,
                    reasoning TEXT NOT NULL,
                    kalshi_url TEXT NOT NULL,
                    entry_cents INTEGER NOT NULL,
                    upside_cents INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    home_crest TEXT,
                    away_crest TEXT,
                    league_emblem TEXT,
                    outcome TEXT DEFAULT 'PENDING',
                    actual_pnl REAL DEFAULT 0.0
                );
            """)

            now_iso = datetime.now(tz=timezone.utc).isoformat()
            for sig in signals:
                entry_cents = int(round(sig.kalshi_implied_prob * 100))
                upside_cents = 100 - entry_cents
                score = int(min(sig.edge * 200, 100))
                conn.execute("""
                    INSERT INTO signal_history (
                        generated_at, event_ticker, market_ticker, match_title,
                        competition, bet_type, description, model_prob,
                        kalshi_implied_prob, edge, confidence, reasoning,
                        kalshi_url, entry_cents, upside_cents, score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(market_ticker) DO UPDATE SET
                        generated_at=excluded.generated_at,
                        model_prob=excluded.model_prob,
                        kalshi_implied_prob=excluded.kalshi_implied_prob,
                        edge=excluded.edge,
                        reasoning=excluded.reasoning,
                        entry_cents=excluded.entry_cents,
                        upside_cents=excluded.upside_cents,
                        score=excluded.score
                """, (
                    now_iso, sig.event_ticker, sig.market_ticker, sig.match_title,
                    sig.competition, sig.bet_type, sig.description, sig.model_prob,
                    sig.kalshi_implied_prob, sig.edge, sig.confidence, sig.reasoning,
                    sig.kalshi_url, entry_cents, upside_cents, score,
                ))
            conn.commit()
            conn.close()
            print(f"  ✓ {len(signals)} signal(s) recorded/updated")
        except Exception as exc:
            print(f"  ✗ Failed to record signal history: {exc}")

    # ── Telegram alerts + ledger logging (opt-in via --telegram) ─────────
    if args.telegram:
        top3 = signals[:3]
        if not top3:
            print("  ⚠  No signals to send via Telegram.")
        else:
            telegram = TelegramClient()
            ledger = Ledger()
            print(f"\n[Telegram] Sending top {len(top3)} signal(s)…")
            for sig in top3:
                try:
                    telegram.send_signal_alert(sig, topic_id=args.topic_id)
                    print(f"  ✓ Sent: {sig.match_title} ({sig.bet_type})")
                except Exception as exc:  # noqa: BLE001
                    print(f"  ✗ Telegram send failed for {sig.match_title}: {exc}")

                try:
                    ledger.log_trade(
                        match=sig.match_title,
                        side=sig.description,
                        stake=10.0,
                        odds=sig.kalshi_odds,
                    )
                    print(f"  ✓ Logged to ledger: {sig.match_title} | {sig.description} @ {sig.kalshi_odds:.2f}")
                except Exception as exc:  # noqa: BLE001
                    print(f"  ✗ Ledger log failed for {sig.match_title}: {exc}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
