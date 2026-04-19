"""Data adapter layer that normalizes football-data.org + Kalshi into a unified schema."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .cache import Cache
from .football_data import FootballDataClient
from .kalshi import KalshiClient, MarketQuote

from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class MatchSnapshot:
    match_id: str
    utc_kickoff: dt.datetime
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    competition: str


@dataclass
class MarketSnapshot:
    match_id: str
    market_id: str
    contract_ticker: str
    implied_prob: float
    model_prob: Optional[float] = None
    ev: Optional[float] = None
    crowd_vs_model: Optional[float] = None


class DataAdapter:
    """High-level facade for pulling normalized match + market data."""

    def __init__(self) -> None:
        self.cache = Cache()
        self.fd_client = FootballDataClient()
        self.kalshi_client = KalshiClient()

    # --- Match data -------------------------------------------------------

    def _normalize_match(self, raw: Dict[str, Any]) -> MatchSnapshot:
        match_id = str(raw.get("id"))
        utc_date = raw.get("utcDate") or raw.get("utc_date")
        kickoff = dt.datetime.fromisoformat(utc_date.replace("Z", "+00:00"))

        home_team = raw.get("homeTeam", {}).get("name", "")
        away_team = raw.get("awayTeam", {}).get("name", "")

        full_time = (raw.get("score") or {}).get("fullTime") or {}
        home_score = full_time.get("homeTeam")
        away_score = full_time.get("awayTeam")

        competition = (raw.get("competition") or {}).get("code") or ""

        return MatchSnapshot(
            match_id=match_id,
            utc_kickoff=kickoff,
            home_team=home_team,
            away_team=away_team,
            home_score=home_score,
            away_score=away_score,
            competition=competition,
        )

    def fetch_matches_incremental(self, last_seen_date: Optional[dt.date]) -> List[MatchSnapshot]:
        raw_matches = self.fd_client.fetch_all_leagues_incremental(last_seen_date)
        snapshots = [self._normalize_match(m) for m in raw_matches]
        return snapshots

    # --- Market data ------------------------------------------------------

    def fetch_markets(self) -> List[MarketQuote]:
        try:
            markets = self.kalshi_client.list_football_markets()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error listing Kalshi markets: %s", exc)
            return []
        quotes: List[MarketQuote] = []
        for m in markets:
            try:
                ob = self.kalshi_client.get_order_book(str(m.get("id")))
                quote = self.kalshi_client.build_market_quote(m, ob)
                quotes.append(quote)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Error fetching order book for market %s: %s", m.get("id"), exc)
        return quotes

    # --- Caching helpers --------------------------------------------------

    def cache_matches(self, key: str, matches: List[MatchSnapshot]) -> None:
        payload = {
            "matches": [
                {
                    "match_id": m.match_id,
                    "utc_kickoff": m.utc_kickoff.isoformat(),
                    "home_team": m.home_team,
                    "away_team": m.away_team,
                    "home_score": m.home_score,
                    "away_score": m.away_score,
                    "competition": m.competition,
                }
                for m in matches
            ]
        }
        self.cache.put(key, payload)

    def load_cached_matches(self, key: str) -> Optional[List[MatchSnapshot]]:
        entry = self.cache.get(key)
        if not entry:
            return None
        matches: List[MatchSnapshot] = []
        for raw in entry.payload.get("matches", []):
            kickoff = dt.datetime.fromisoformat(raw["utc_kickoff"])
            matches.append(
                MatchSnapshot(
                    match_id=str(raw["match_id"]),
                    utc_kickoff=kickoff,
                    home_team=str(raw["home_team"]),
                    away_team=str(raw["away_team"]),
                    home_score=raw.get("home_score"),
                    away_score=raw.get("away_score"),
                    competition=str(raw.get("competition", "")),
                )
            )
        return matches
