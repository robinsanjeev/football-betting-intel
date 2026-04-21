"""⚠️ DEPRECATED — This demo uses the old naive Poisson model and is superseded by run_signals.py. Kept for reference only.

Original description:
End-to-end sanity-check flow for one league + Kalshi markets.

This script:
- Loads config and logger
- Pulls incremental matches for the first configured league
- Pulls Kalshi football markets
- Wires a trivial Poisson-based model into the hybrid model interface
- Computes a rough EV vs implied probabilities
- Prints out any positive-EV opportunities (no real betting; console only)

Run with:

    cd ~/.openclaw/workspace
    python -m football_intel.scripts.demo_flow
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, List

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger
from football_intel.ingestion.adapters import DataAdapter
from football_intel.ingestion.kalshi import MarketQuote
from football_intel.models.poisson import PoissonParams, outcome_probs
from football_intel.strategy.ev import EVResult, expected_value, implied_prob_from_price, should_bet
from football_intel.strategy.sentiment import compute_crowd_vs_model

logger = get_logger(__name__)


# --- Simple stub regressor -------------------------------------------------

@dataclass
class DummyRegressor:
    """Placeholder regressor.

    For now, we just return the Poisson 1X2 probs unchanged. Replace this with
    a trained XGBoost/sklearn model by implementing predict_proba.
    """

    def predict_proba(self, X: Any) -> List[List[float]]:  # pragma: no cover - demo
        # X is [[p_home_poisson, p_draw_poisson, p_away_poisson]]
        return [X[0]]


# --- Helper functions ------------------------------------------------------


def pick_league(matches, league_code: str):
    return [m for m in matches if m.competition == league_code]


def build_naive_poisson_params() -> PoissonParams:
    """Naive Poisson params as a starting point.

    TODO: replace with calibrated lambdas learned from historical data.
    """

    return PoissonParams(lambda_home=1.4, lambda_away=1.1)


def compute_ev_for_market(quote: MarketQuote, model_home_prob: float, stake: float = 10.0) -> EVResult:
    """Compute EV for a YES-style contract on the HOME side.

    This assumes a simplified payoff structure: if the contract pays $1 for a
    price p, the potential profit on a $stake position is roughly:

        stake * (1 / p_implied - 1)

    Adjust this once you finalize the Kalshi payout math (fees, etc.).
    """

    implied = implied_prob_from_price(quote.last_price)
    # Avoid division by zero
    if implied <= 0:
        implied = 1e-6
    potential_profit = stake * (1.0 / implied - 1.0)
    return expected_value(model_home_prob, potential_profit, stake)


# --- Main pipeline ---------------------------------------------------------


def main() -> None:  # pragma: no cover - script entrypoint
    cfg = load_config()
    league_code = cfg.football_data.leagues[0] if cfg.football_data.leagues else "PL"
    logger.info("Running demo flow for league %s", league_code)

    adapter = DataAdapter()

    # For the demo, just use today's date as the starting point
    today = dt.date.today()
    matches = adapter.fetch_matches_incremental(last_seen_date=today)
    league_matches = pick_league(matches, league_code)
    logger.info("Fetched %d matches for league %s", len(league_matches), league_code)

    markets = adapter.fetch_markets()
    logger.info("Fetched %d Kalshi markets", len(markets))

    if not league_matches or not markets:
        logger.warning("No matches or markets available for demo; exiting.")
        return

    # Naive Poisson-only model for now
    params = build_naive_poisson_params()
    probs = outcome_probs(params)
    home_prob = probs["HOME"]

    logger.info("Naive Poisson HOME win prob: %.3f", home_prob)

    # Just pair the first match with the first market for this demo
    match = league_matches[0]
    market = markets[0]

    logger.info("Demo match: %s vs %s at %s", match.home_team, match.away_team, match.utc_kickoff)
    logger.info("Demo market: %s (%s)", market.contract_ticker, market.market_id)

    ev_result = compute_ev_for_market(market, model_home_prob=home_prob, stake=10.0)
    crowd = compute_crowd_vs_model(
        implied_prob=implied_prob_from_price(market.last_price),
        model_prob=home_prob,
    )

    if should_bet(ev_result):
        print("\n=== POSITIVE-EV SIGNAL (DEMO ONLY) ===")
        print(f"Match: {match.home_team} vs {match.away_team}")
        print(f"Kickoff (UTC): {match.utc_kickoff}")
        print(f"Recommended side: HOME")
        print(f"Model HOME prob: {home_prob:.1%}")
        print(f"Market implied prob: {crowd.implied_prob:.1%}")
        print(f"EV (per $10): ${ev_result.ev:0.2f}")
        print(f"Kalshi ticker: {market.contract_ticker} (market_id={market.market_id})")
    else:
        print("\nNo positive-EV signal in this demo pairing (HOME side).")


if __name__ == "__main__":
    main()
