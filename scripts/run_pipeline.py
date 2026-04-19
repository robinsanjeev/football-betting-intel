"""Production pipeline runner — dual-track: Match + Futures.

Track 1 (Match): football-data.org matches + Odds API odds + Poisson model → per-match EV
Track 2 (Futures): Kalshi soccer futures + heuristic model → season-level signals

Both tracks send alerts to Telegram and log to the paper-trading ledger.

Run with:
    cd ~/.openclaw/workspace
    python3 -m football_intel.scripts.run_pipeline
"""

from __future__ import annotations

import datetime as dt
import traceback
from typing import List, Optional

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger
from football_intel.ingestion.adapters import DataAdapter, MatchSnapshot
from football_intel.ingestion.odds_api import OddsApiClient, MatchOdds
from football_intel.ingestion.kalshi_futures import KalshiFuturesClient
from football_intel.models.poisson import PoissonParams, outcome_probs
from football_intel.models.futures_model import evaluate_futures_market
from football_intel.strategy.ev import expected_value, should_bet
from football_intel.strategy.sentiment import compute_crowd_vs_model
from football_intel.delivery.telegram_bot import BetAlert, TelegramClient
from football_intel.tracking.ledger import Ledger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_poisson_params() -> PoissonParams:
    """Naive baseline Poisson params. TODO: calibrate from DB."""
    return PoissonParams(lambda_home=1.45, lambda_away=1.15)


def fuzzy_match_name(name_a: str, name_b: str) -> bool:
    """Check if two team names likely refer to the same team."""
    a = name_a.lower().strip()
    b = name_b.lower().strip()
    if a == b:
        return True
    # Check if one is a substring of the other
    if a in b or b in a:
        return True
    # Check common abbreviations (e.g., "FC" suffix/prefix)
    a_clean = a.replace(" fc", "").replace("fc ", "").strip()
    b_clean = b.replace(" fc", "").replace("fc ", "").strip()
    if a_clean == b_clean:
        return True
    if a_clean in b_clean or b_clean in a_clean:
        return True
    return False


def pair_matches_with_odds(
    matches: List[MatchSnapshot],
    odds: List[MatchOdds],
) -> List[tuple]:
    """Pair football-data.org matches with Odds API odds by team name fuzzy match."""
    pairs = []
    used_odds = set()
    for match in matches:
        for i, od in enumerate(odds):
            if i in used_odds:
                continue
            if (fuzzy_match_name(match.home_team, od.home_team) and
                    fuzzy_match_name(match.away_team, od.away_team)):
                pairs.append((match, od))
                used_odds.add(i)
                break
            # Try reversed (different naming conventions)
            if (fuzzy_match_name(match.home_team, od.away_team) and
                    fuzzy_match_name(match.away_team, od.home_team)):
                pairs.append((match, od))
                used_odds.add(i)
                break
    return pairs


# ---------------------------------------------------------------------------
# Track 1: Match-level signals (football-data.org + Odds API + Poisson)
# ---------------------------------------------------------------------------

def run_match_track(tg: TelegramClient, ledger: Ledger) -> int:
    """Run the per-match betting signal track. Returns number of signals sent."""
    signals_sent = 0
    adapter = DataAdapter()
    odds_client = OddsApiClient()

    # Fetch matches
    logger.info("[Match Track] Fetching matches...")
    matches = adapter.fetch_matches_incremental(last_seen_date=dt.date.today())
    upcoming = [m for m in matches if m.home_score is None and m.away_score is None]
    logger.info("[Match Track] %d upcoming matches", len(upcoming))

    if not upcoming:
        logger.info("[Match Track] No upcoming matches. Skipping.")
        return 0

    # Fetch live odds
    logger.info("[Match Track] Fetching live odds from Odds API...")
    try:
        all_odds = odds_client.get_all_soccer_odds()
    except Exception as exc:
        logger.exception("[Match Track] Error fetching odds: %s", exc)
        all_odds = []

    if not all_odds:
        logger.info("[Match Track] No odds available. Skipping.")
        return 0

    # Pair matches with odds
    pairs = pair_matches_with_odds(upcoming, all_odds)
    logger.info("[Match Track] %d match↔odds pairs found", len(pairs))

    # Model + EV
    params = build_poisson_params()
    probs = outcome_probs(params)

    for match, odds in pairs:
        for side, prob_key in [("HOME", "HOME"), ("DRAW", "DRAW"), ("AWAY", "AWAY")]:
            model_prob = probs[prob_key]

            # Get implied prob from bookmaker odds
            if side == "HOME" and odds.implied_home_prob:
                implied = odds.implied_home_prob
                best_odds = odds.best_home_odds or 0
            elif side == "DRAW" and odds.implied_draw_prob:
                implied = odds.implied_draw_prob
                best_odds = odds.best_draw_odds or 0
            elif side == "AWAY" and odds.implied_away_prob:
                implied = odds.implied_away_prob
                best_odds = odds.best_away_odds or 0
            else:
                continue

            if implied <= 0 or best_odds <= 1:
                continue

            # EV = (model_prob * profit) - ((1 - model_prob) * stake)
            stake = 10.0
            potential_profit = stake * (best_odds - 1.0)
            ev_result = expected_value(model_prob, potential_profit, stake)

            if should_bet(ev_result):
                sentiment = compute_crowd_vs_model(implied, model_prob)

                alert = BetAlert(
                    match=f"{match.home_team} vs {match.away_team}",
                    kickoff_utc=match.utc_kickoff.strftime("%Y-%m-%d %H:%M UTC"),
                    side=side,
                    model_prob=model_prob,
                    implied_prob=implied,
                    ev=ev_result.ev,
                )

                try:
                    tg.send_bet_alert(alert)
                    signals_sent += 1
                    logger.info(
                        "[Match Track] Signal: %s %s, EV=$%.2f, model=%.1f%%, implied=%.1f%%",
                        alert.match, side, ev_result.ev,
                        model_prob * 100, implied * 100,
                    )
                except Exception as exc:
                    logger.exception("[Match Track] Telegram send failed: %s", exc)

                ledger.log_trade(
                    match=f"{match.home_team} vs {match.away_team}",
                    side=side,
                    stake=stake,
                    odds=best_odds,
                )

    return signals_sent


# ---------------------------------------------------------------------------
# Track 2: Futures signals (Kalshi soccer futures)
# ---------------------------------------------------------------------------

def run_futures_track(tg: TelegramClient, ledger: Ledger) -> int:
    """Run the Kalshi soccer futures signal track. Returns number of signals sent."""
    signals_sent = 0
    futures_client = KalshiFuturesClient()

    logger.info("[Futures Track] Fetching Kalshi soccer futures...")
    try:
        futures = futures_client.fetch_soccer_futures()
    except Exception as exc:
        logger.exception("[Futures Track] Error fetching Kalshi futures: %s", exc)
        return 0

    logger.info("[Futures Track] %d soccer futures markets", len(futures))

    for fm in futures:
        if fm.implied_prob_yes is None or fm.implied_prob_yes <= 0:
            continue

        signal = evaluate_futures_market(
            event_ticker=fm.event_ticker,
            event_title=fm.event_title,
            market_ticker=fm.market_ticker,
            market_title=fm.market_title,
            implied_prob=fm.implied_prob_yes,
        )

        if signal and signal.ev and signal.ev > 0:
            msg = (
                f"📊 Futures Signal\n"
                f"Event: {signal.event_title}\n"
                f"Market: {signal.market_title}\n"
                f"Type: {signal.signal_type}\n"
                f"Implied prob: {signal.market_implied_prob:.1%}\n"
                f"Model prob: {signal.model_prob:.1%}\n"
                f"EV (per $10): ${signal.ev:.2f}\n"
                f"Kalshi: https://kalshi.com/markets/{signal.market_ticker}"
            )

            try:
                tg.send_message(msg)
                signals_sent += 1
                logger.info(
                    "[Futures Track] Signal: %s — %s, EV=$%.2f",
                    signal.event_title, signal.market_title, signal.ev,
                )
            except Exception as exc:
                logger.exception("[Futures Track] Telegram send failed: %s", exc)

            # Log to ledger
            ledger.log_trade(
                match=f"[FUTURES] {signal.event_title}",
                side=signal.market_title,
                stake=10.0,
                odds=1.0 / signal.market_implied_prob if signal.market_implied_prob > 0 else 0,
            )

    return signals_sent


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    tg = TelegramClient()
    ledger = Ledger()

    logger.info("=" * 60)
    logger.info("Football Intel Pipeline — starting dual-track run")
    logger.info("=" * 60)

    # Track 1: Match-level
    match_signals = run_match_track(tg, ledger)

    # Track 2: Futures
    futures_signals = run_futures_track(tg, ledger)

    total = match_signals + futures_signals
    logger.info(
        "Pipeline complete: %d match signals + %d futures signals = %d total",
        match_signals, futures_signals, total,
    )


def main() -> None:
    try:
        run()
    except Exception:
        tb = traceback.format_exc()
        logger.error("Pipeline crashed:\n%s", tb)
        try:
            tg = TelegramClient()
            tg.send_message(f"⚠️ *Football Intel Pipeline Error*\n```\n{tb[:3000]}\n```")
        except Exception:
            logger.error("Could not send Telegram error notification")


if __name__ == "__main__":
    main()
