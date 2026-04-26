"""Standalone odds snapshot script.

Fetches current Kalshi markets and model predictions, then records
odds snapshots for all markets. Designed to run from cron.

Usage:
    cd ~/.openclaw/workspace
    python3 -m football_intel.scripts.take_odds_snapshot
"""

from __future__ import annotations

import sys

from football_intel.common.logging_utils import get_logger
from football_intel.ingestion.kalshi_soccer import KalshiSoccerClient
from football_intel.ingestion.odds_tracker import OddsTracker
from football_intel.models.calibrated_poisson import CalibratedPoissonModel
from football_intel.models.historical_data import load_historical_results
from football_intel.strategy.signal_generator import SignalGenerator, _get_model_prob_for_market

logger = get_logger(__name__)


def main() -> None:
    print("=== Football Intel — Odds Snapshot ===\n")

    # 1. Load historical data and calibrate model
    print("1. Loading historical results...")
    try:
        results = load_historical_results()
        print(f"   Loaded {len(results)} historical results")
    except Exception as exc:
        print(f"   ✗ Failed to load historical data: {exc}")
        sys.exit(1)

    print("2. Calibrating Poisson model...")
    model = CalibratedPoissonModel()
    model.calibrate(results)
    print("   ✓ Model calibrated")

    # 2. Fetch current Kalshi markets
    print("3. Fetching Kalshi soccer markets...")
    try:
        client = KalshiSoccerClient()
        matches = client.fetch_match_markets()
        print(f"   Found {len(matches)} matches")
    except Exception as exc:
        print(f"   ✗ Failed to fetch Kalshi markets: {exc}")
        sys.exit(1)

    if not matches:
        print("   No matches to snapshot. Done.")
        return

    # 3. Generate market data tuples for snapshot
    print("4. Computing model probabilities for all markets...")
    market_data = []  # list of (market_ticker, kalshi_prob, model_prob)

    for match in matches:
        try:
            prediction = model.predict_from_kalshi_match(match)
        except Exception:
            continue

        for market in match.markets:
            if market.yes_ask is None or market.yes_ask <= 0:
                continue

            kalshi_prob = market.yes_ask
            result = _get_model_prob_for_market(market, prediction)
            if result is None:
                continue

            model_prob, _ = result
            market_data.append((market.market_ticker, kalshi_prob, model_prob))

    print(f"   Computed {len(market_data)} market probabilities")

    # 4. Take snapshot
    print("5. Recording odds snapshots...")
    tracker = OddsTracker()
    count = tracker.take_snapshot(market_data)
    print(f"   ✓ Recorded {count} snapshots")

    print(f"\nDone. {count} odds snapshots recorded.")


if __name__ == "__main__":
    main()
