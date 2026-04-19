"""Kalshi soccer futures markets client.

Fetches season-level soccer/football events from Kalshi (league champions,
player awards, transfer markets, etc.) and normalizes them for the futures
modeling track.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger
from football_intel.ingestion.kalshi import KalshiClient, _sign_request

logger = get_logger(__name__)

# Mapping from football-data.org TIER_ONE competitions to Kalshi title/ticker keywords.
# Only futures matching these will be included.
TIER_ONE_SOCCER_KEYWORDS = {
    # PL — Premier League
    "PL": ["premier league", "pfa player of the year", "manchester united",
           "manchester city", "arsenal", "liverpool", "chelsea", "tottenham",
           "newcastle", "west ham", "aston villa", "brighton", "brentford",
           "fulham", "bournemouth", "nottingham", "wolves", "everton",
           "crystal palace", "leicester", "ipswich", "southampton"],
    # PD — La Liga
    "PD": ["la liga", "barcelona", "real madrid", "atletico madrid",
           "sevilla", "real betis", "villarreal", "real sociedad",
           "athletic bilbao", "girona", "celta vigo", "getafe",
           "mallorca", "valencia", "osasuna", "rayo vallecano",
           "espanyol", "alaves", "las palmas", "leganes",
           "lamine yamal"],
    # BL1 — Bundesliga
    "BL1": ["bundesliga", "bayern munich", "borussia dortmund",
            "rb leipzig", "bayer leverkusen", "eintracht frankfurt",
            "wolfsburg", "freiburg", "hoffenheim", "union berlin",
            "stuttgart", "werder bremen", "mainz", "augsburg",
            "monchengladbach", "heidenheim", "bochum", "darmstadt",
            "st. pauli", "holstein kiel"],
    # SA — Serie A
    "SA": ["serie a", "inter milan", "ac milan", "juventus", "napoli",
           "roma", "lazio", "atalanta", "fiorentina", "bologna",
           "torino", "monza", "genoa", "cagliari", "udinese",
           "sassuolo", "lecce", "empoli", "verona", "salernitana",
           "como", "parma", "venezia"],
    # FL1 — Ligue 1
    "FL1": ["ligue 1", "paris saint-germain", "psg", "marseille",
            "lyon", "monaco", "lille", "nice", "rennes", "lens",
            "strasbourg", "toulouse", "montpellier", "nantes",
            "reims", "brest", "lorient", "clermont", "metz",
            "le havre", "auxerre", "angers", "saint-etienne"],
    # CL — Champions League
    "CL": ["champions league", "ucl"],
    # BSA — Brasileiro Serie A
    "BSA": ["brasileiro", "brasileir"],
    # WC — World Cup
    "WC": ["world cup", "fifa"],
    # EC — European Championship
    "EC": ["euro 20", "european championship"],
    # General soccer awards
    "AWARDS": ["ballon d'or", "ballon d\\u2019or", "ballondor",
               "cristiano ronaldo", "golden boot"],
}

# Flatten all keywords into a single list for matching
ALL_TIER_ONE_KEYWORDS = []
for _keywords in TIER_ONE_SOCCER_KEYWORDS.values():
    ALL_TIER_ONE_KEYWORDS.extend(_keywords)


@dataclass
class FuturesMarket:
    event_ticker: str
    event_title: str
    category: str
    market_ticker: str
    market_title: str
    yes_ask: Optional[float]
    no_ask: Optional[float]
    last_price: Optional[float]
    implied_prob_yes: Optional[float]


class KalshiFuturesClient:
    def __init__(self) -> None:
        self.kc = KalshiClient()

    def _auth_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Authenticated GET using the base KalshiClient's credentials."""
        url = f"{self.kc.base_url}{path}"
        timestamp_ms = str(int(dt.datetime.now().timestamp() * 1000))
        full_path = urlparse(url).path
        sig = _sign_request(self.kc.private_key, timestamp_ms, "GET", full_path)
        headers = {
            "KALSHI-ACCESS-KEY": self.kc.key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": sig,
        }
        resp = self.kc.session.get(url, headers=headers, params=params or {}, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def fetch_soccer_futures(self) -> List[FuturesMarket]:
        """Fetch all open soccer/football futures events from Kalshi.

        Paginates through events, filters to Sports category + soccer keywords,
        and returns normalized FuturesMarket objects.
        """
        all_futures: List[FuturesMarket] = []
        cursor = None

        for page in range(20):  # safety limit
            params: Dict[str, Any] = {
                "limit": 200,
                "status": "open",
                "with_nested_markets": True,
            }
            if cursor:
                params["cursor"] = cursor

            try:
                data = self._auth_get("/events", params=params)
            except Exception as exc:
                logger.exception("Error fetching Kalshi events page %d: %s", page, exc)
                break

            events = data.get("events", [])
            if not events:
                break

            for ev in events:
                cat = ev.get("category", "")
                title = (ev.get("title") or "").lower()
                event_ticker = ev.get("event_ticker", "")

                # Filter: must be Sports category AND match a TIER_ONE soccer keyword
                if cat != "Sports":
                    continue
                ticker_lower = event_ticker.lower()
                is_tier_one_soccer = any(
                    kw in title or kw in ticker_lower
                    for kw in ALL_TIER_ONE_KEYWORDS
                )
                if not is_tier_one_soccer:
                    continue

                markets = ev.get("markets", [])
                for m in markets:
                    yes_ask = m.get("yes_ask_dollars")
                    no_ask = m.get("no_ask_dollars")
                    last_price = m.get("last_price_dollars")

                    # Implied probability from yes_ask
                    implied = None
                    if yes_ask and float(yes_ask) > 0:
                        implied = float(yes_ask)  # Kalshi prices are already 0-1 probabilities

                    all_futures.append(
                        FuturesMarket(
                            event_ticker=event_ticker,
                            event_title=ev.get("title", ""),
                            category=cat,
                            market_ticker=m.get("ticker", ""),
                            market_title=m.get("title", ""),
                            yes_ask=float(yes_ask) if yes_ask else None,
                            no_ask=float(no_ask) if no_ask else None,
                            last_price=float(last_price) if last_price else None,
                            implied_prob_yes=implied,
                        )
                    )

            cursor = data.get("cursor")
            if not cursor:
                break

        logger.info("kalshi-futures: found %d soccer futures markets", len(all_futures))
        return all_futures
