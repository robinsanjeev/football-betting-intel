"""Simple futures/season-outcome model.

For league champion markets, we use current standings + points-per-game
projections to estimate title probabilities. For player/transfer markets,
we use a simpler heuristic based on market sentiment.

TODO: Replace with a proper Elo/Monte Carlo simulation once historical
standings data is available in the DB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class FuturesSignal:
    event_ticker: str
    event_title: str
    market_ticker: str
    market_title: str
    market_implied_prob: float
    model_prob: Optional[float]
    ev: Optional[float]
    signal_type: str  # "league_champion", "player_award", "transfer", "other"


def classify_market(event_title: str, market_title: str) -> str:
    """Classify a futures market into a signal type."""
    title = (event_title + " " + market_title).lower()
    if any(kw in title for kw in ["champion", "winner", "liga", "serie", "ligue", "mls cup", "brasileir"]):
        return "league_champion"
    if any(kw in title for kw in ["ballon", "pfa", "player of the year"]):
        return "player_award"
    if any(kw in title for kw in ["leave", "next", "join", "transfer", "ronaldo"]):
        return "transfer"
    return "other"


def evaluate_futures_market(
    event_ticker: str,
    event_title: str,
    market_ticker: str,
    market_title: str,
    implied_prob: float,
    stake: float = 10.0,
) -> Optional[FuturesSignal]:
    """Evaluate a Kalshi futures market for potential value.

    For now, we use a simple heuristic:
    - If implied prob is very low (<15%) but the market is about a plausible
      outcome (e.g., a top-4 team winning the league), flag it as potential value.
    - If implied prob is very high (>85%), skip (no edge).

    TODO: Replace with proper Elo-based title probability model.
    """
    signal_type = classify_market(event_title, market_title)

    # Simple heuristic model probability (placeholder)
    # In reality this would come from standings + Elo + Monte Carlo sim
    model_prob = None
    ev = None

    # For league champions, we flag markets where implied prob is low enough
    # that there might be value (crowd underpricing a contender)
    if 0.05 <= implied_prob <= 0.40:
        # Naive: assume model prob = implied + small edge for contenders
        # This is a placeholder; real model would use standings data
        model_prob = implied_prob * 1.1  # assume 10% edge as placeholder
        potential_profit = stake * (1.0 / implied_prob - 1.0)
        ev = (model_prob * potential_profit) - ((1.0 - model_prob) * stake)

    if ev is not None and ev > 0:
        return FuturesSignal(
            event_ticker=event_ticker,
            event_title=event_title,
            market_ticker=market_ticker,
            market_title=market_title,
            market_implied_prob=implied_prob,
            model_prob=model_prob,
            ev=ev,
            signal_type=signal_type,
        )

    return None
