"""Client for The Odds API (https://the-odds-api.com).

Provides real-time match-level odds from multiple bookmakers for soccer leagues.
Free tier: 500 requests/month. Each sport+region+market combo = 1 request.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class MatchOdds:
    event_id: str
    sport_key: str
    home_team: str
    away_team: str
    commence_time: str  # ISO 8601
    bookmakers: List[Dict[str, Any]]
    # Derived fields
    best_home_odds: Optional[float] = None
    best_draw_odds: Optional[float] = None
    best_away_odds: Optional[float] = None
    implied_home_prob: Optional[float] = None
    implied_draw_prob: Optional[float] = None
    implied_away_prob: Optional[float] = None


class OddsApiClient:
    def __init__(self) -> None:
        cfg = load_config().odds_api
        self.base_url = cfg.base_url.rstrip("/")
        self.api_key = cfg.api_key
        self.regions = cfg.regions
        self.markets = cfg.markets
        self.sports = cfg.sports

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        all_params = {"apiKey": self.api_key}
        if params:
            all_params.update(params)
        logger.debug("GET %s", url)
        resp = requests.get(url, params=all_params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def list_sports(self) -> List[Dict[str, Any]]:
        """List in-season sports (free, doesn't count against quota)."""
        return self._get("sports")

    def get_odds_for_sport(self, sport_key: str) -> List[MatchOdds]:
        """Get upcoming match odds for a given sport key.

        Each call costs 1 quota unit per region specified.
        """
        raw = self._get(
            f"sports/{sport_key}/odds",
            params={
                "regions": self.regions,
                "markets": self.markets,
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
        )

        results: List[MatchOdds] = []
        for event in raw:
            match_odds = self._parse_event(event, sport_key)
            if match_odds:
                results.append(match_odds)
        return results

    def get_all_soccer_odds(self) -> List[MatchOdds]:
        """Fetch odds for all configured soccer sports.

        Costs 1 quota unit per sport per region.
        """
        all_odds: List[MatchOdds] = []
        for sport in self.sports:
            try:
                odds = self.get_odds_for_sport(sport)
                all_odds.extend(odds)
                logger.info("odds-api: %d matches for %s", len(odds), sport)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Error fetching odds for %s: %s", sport, exc)
        logger.info("odds-api: %d total matches across %d sports", len(all_odds), len(self.sports))
        return all_odds

    def _parse_event(self, event: Dict[str, Any], sport_key: str) -> Optional[MatchOdds]:
        """Parse a single event response into a MatchOdds object."""
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        commence_time = event.get("commence_time", "")
        event_id = event.get("id", "")
        bookmakers = event.get("bookmakers", [])

        # Find best odds across all bookmakers for h2h market
        best_home = 0.0
        best_draw = 0.0
        best_away = 0.0

        for bm in bookmakers:
            for market in bm.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}
                home_price = outcomes.get(home_team, 0.0)
                away_price = outcomes.get(away_team, 0.0)
                draw_price = outcomes.get("Draw", 0.0)
                best_home = max(best_home, home_price)
                best_draw = max(best_draw, draw_price)
                best_away = max(best_away, away_price)

        # Compute implied probabilities from best odds (1/odds, then normalize)
        implied_home = (1.0 / best_home) if best_home > 0 else None
        implied_draw = (1.0 / best_draw) if best_draw > 0 else None
        implied_away = (1.0 / best_away) if best_away > 0 else None

        return MatchOdds(
            event_id=event_id,
            sport_key=sport_key,
            home_team=home_team,
            away_team=away_team,
            commence_time=commence_time,
            bookmakers=bookmakers,
            best_home_odds=best_home if best_home > 0 else None,
            best_draw_odds=best_draw if best_draw > 0 else None,
            best_away_odds=best_away if best_away > 0 else None,
            implied_home_prob=implied_home,
            implied_draw_prob=implied_draw,
            implied_away_prob=implied_away,
        )
