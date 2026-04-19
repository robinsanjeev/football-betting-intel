"""Kalshi match-level soccer markets client.

Fetches individual match betting markets from Kalshi for EPL, Bundesliga,
and UCL — moneylines, first-half lines, spreads, totals, and BTTS.

Auth is handled by the base KalshiClient (RSA-PSS signed requests).
This client focuses purely on per-match bet types, not season-level futures.

Series tickers covered:
  EPL:        KXEPLGAME, KXEPL1H, KXEPLSPREAD, KXEPLTOTAL, KXEPLBTTS
  Bundesliga: KXBUNDESLIGAGAME, KXBUNDESLIGA1H, KXBUNDESLIGASPREAD,
              KXBUNDESLIGATOTAL, KXBUNDESLIGABTTS
  UCL:        KXUCLGAME
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from football_intel.common.logging_utils import get_logger
from football_intel.ingestion.kalshi import KalshiClient

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Series tickers — exactly as specified
# ---------------------------------------------------------------------------

SERIES_TICKERS: List[str] = [
    # EPL
    "KXEPLGAME",
    "KXEPL1H",
    "KXEPLSPREAD",
    "KXEPLTOTAL",
    "KXEPLBTTS",
    # Bundesliga
    "KXBUNDESLIGAGAME",
    "KXBUNDESLIGA1H",
    "KXBUNDESLIGASPREAD",
    "KXBUNDESLIGATOTAL",
    "KXBUNDESLIGABTTS",
    # UCL
    "KXUCLGAME",
]

# ---------------------------------------------------------------------------
# Bet-type classification from series_ticker suffix
# ---------------------------------------------------------------------------

# Ordered so longer/more-specific suffixes are checked first
_BET_TYPE_SUFFIXES = [
    ("SPREAD", "SPREAD"),
    ("TOTAL", "OVER_UNDER"),
    ("BTTS", "BTTS"),
    ("GAME", "MONEYLINE"),
    ("1H", "FIRST_HALF"),
]


def _classify_bet_type(series_ticker: str) -> str:
    """Return the canonical bet type string from a series_ticker."""
    upper = series_ticker.upper()
    for suffix, bet_type in _BET_TYPE_SUFFIXES:
        if upper.endswith(suffix):
            return bet_type
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Competition detection from series_ticker prefix
# ---------------------------------------------------------------------------

def _detect_competition(series_ticker: str) -> str:
    """Return 'EPL', 'Bundesliga', or 'UCL' from a series_ticker."""
    upper = series_ticker.upper()
    if upper.startswith("KXEPL"):
        return "EPL"
    if upper.startswith("KXBUNDESLIGA"):
        return "Bundesliga"
    if upper.startswith("KXUCL"):
        return "UCL"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Team name parsing from event titles
# ---------------------------------------------------------------------------

# Strip known market-type suffixes from event titles
_TITLE_SUFFIXES = re.compile(
    r":\s*(Totals?|Spreads?|BTTS|Both Teams to Score|First Half|1H)\s*$",
    re.IGNORECASE,
)


def _strip_market_suffix(title: str) -> str:
    """Remove ' : Totals', ': Spreads', etc. from the end of a title."""
    return _TITLE_SUFFIXES.sub("", title).strip()


def _parse_teams(title: str) -> tuple[str, str]:
    """Parse (home_team, away_team) from an event title.

    Supported formats:
      "Chelsea vs Manchester United"    → home=Chelsea, away=Man Utd
      "Manchester United at Chelsea"    → home=Chelsea, away=Man Utd
      (with optional ': Totals' suffix stripped first)
    """
    base = _strip_market_suffix(title)

    # "X at Y" → away=X, home=Y
    at_match = re.match(r"^(.+?)\s+at\s+(.+)$", base, re.IGNORECASE)
    if at_match:
        away = at_match.group(1).strip()
        home = at_match.group(2).strip()
        return home, away

    # "X vs Y" → home=X, away=Y
    vs_match = re.match(r"^(.+?)\s+vs\.?\s+(.+)$", base, re.IGNORECASE)
    if vs_match:
        home = vs_match.group(1).strip()
        away = vs_match.group(2).strip()
        return home, away

    # Fallback: can't parse cleanly
    logger.warning("Could not parse teams from title: %r", title)
    return base, ""


# ---------------------------------------------------------------------------
# Match key extraction from event_ticker
# ---------------------------------------------------------------------------

# event_ticker format: KXEPLGAME-26APR18CFCMUN
#                                ^-----------^ date+teams suffix
_TICKER_SUFFIX_RE = re.compile(r"^[A-Z0-9]+-(.+)$")


def _match_key_from_ticker(event_ticker: str) -> str:
    """Extract the date+teams suffix used to group markets for the same match.

    e.g. 'KXEPLGAME-26APR18CFCMUN' → '26APR18CFCMUN'
         'KXEPLSPREAD-26APR18CFCMUN' → '26APR18CFCMUN'
    """
    m = _TICKER_SUFFIX_RE.match(event_ticker)
    if m:
        return m.group(1)
    # If there is no hyphen, use the whole ticker as fallback
    return event_ticker


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SoccerMarket:
    """A single Kalshi contract within a soccer match event."""

    market_ticker: str
    market_title: str
    bet_type: str          # MONEYLINE, FIRST_HALF, SPREAD, OVER_UNDER, BTTS
    yes_sub_title: str
    no_sub_title: str
    yes_ask: Optional[float]   # dollars (0-1 scale on Kalshi)
    no_ask: Optional[float]    # dollars
    last_price: Optional[float]
    implied_prob_yes: Optional[float]  # yes_ask as a 0-1 probability
    line: Optional[float]   # numeric line for SPREAD / OVER_UNDER (e.g. 2.5)
    side: Optional[str]     # MONEYLINE: HOME/AWAY/DRAW; SPREAD: team name


@dataclass
class SoccerMatch:
    """All bet markets for a single soccer fixture."""

    event_ticker: str
    event_title: str
    competition: str         # EPL, Bundesliga, UCL
    home_team: str
    away_team: str
    kickoff_utc: Optional[datetime]
    markets: List[SoccerMarket] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Price helpers
# ---------------------------------------------------------------------------

def _cents_to_dollars(value: Any) -> Optional[float]:
    """Convert a cents integer to dollars.  Returns None for missing/zero."""
    if value is None:
        return None
    v = float(value)
    # Kalshi sometimes returns already-dollar prices (0-1) via *_dollars fields;
    # if the field name ends in _dollars it is already normalised.
    return v if v != 0.0 else None


def _parse_line(title: str) -> Optional[float]:
    """Extract the numeric handicap / total from a market title.

    Matches patterns like '2.5', '-1.5', '+2'.
    """
    m = re.search(r"([+-]?\d+(?:\.\d+)?)", title)
    return float(m.group(1)) if m else None


def _parse_side(market_title: str, yes_sub_title: str, home_team: str, away_team: str, bet_type: str) -> Optional[str]:
    """Determine 'HOME', 'AWAY', 'DRAW', or a team name for SPREAD markets."""
    if bet_type == "MONEYLINE":
        text = yes_sub_title.lower()
        if "draw" in text or "tie" in text:
            return "DRAW"
        if home_team and home_team.lower() in text:
            return "HOME"
        if away_team and away_team.lower() in text:
            return "AWAY"
        # Fallback: if title says 'home' / 'away'
        if "home" in text:
            return "HOME"
        if "away" in text:
            return "AWAY"
        return None

    if bet_type == "SPREAD":
        # Return the team name the spread applies to (from the yes_sub_title)
        for team in (home_team, away_team):
            if team and team.lower() in yes_sub_title.lower():
                return team
        return None

    return None


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class KalshiSoccerClient:
    """Fetch match-level soccer betting markets from Kalshi.

    Uses the /events endpoint filtered by series_ticker, paginates results,
    groups events by match, and returns structured SoccerMatch objects.
    """

    # Seconds to sleep between series-ticker requests to respect rate limits
    _INTER_REQUEST_SLEEP = 0.25

    def __init__(self) -> None:
        # Reuse the KalshiClient for auth and session management
        self._kc = KalshiClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_match_markets(self) -> List[SoccerMatch]:
        """Fetch all current match-level soccer markets, grouped by match.

        Returns a list of SoccerMatch objects, each containing all its
        markets across available bet types (moneyline, spread, total, etc.).
        """
        # Step 1: Fetch all raw events for every series ticker
        raw_events: List[Dict[str, Any]] = []
        for series_ticker in SERIES_TICKERS:
            events = self._fetch_events_for_series(series_ticker)
            raw_events.extend(events)
            logger.info(
                "series=%s → %d events fetched", series_ticker, len(events)
            )
            time.sleep(self._INTER_REQUEST_SLEEP)

        # Step 2: Group events by match key (date+teams suffix)
        #         and accumulate markets per group
        match_groups: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "events": [],   # list of raw event dicts
            "markets": [],  # accumulated SoccerMarket objects
        })

        for ev in raw_events:
            event_ticker = ev.get("event_ticker", "")
            match_key = _match_key_from_ticker(event_ticker)
            match_groups[match_key]["events"].append(ev)

            series_ticker = ev.get("series_ticker", "")
            bet_type = _classify_bet_type(series_ticker)
            competition = _detect_competition(series_ticker)

            for mkt in ev.get("markets", []):
                soccer_market = self._parse_market(mkt, bet_type, ev)
                match_groups[match_key]["markets"].append(soccer_market)

        # Step 3: Build SoccerMatch objects — pick a canonical event per group
        results: List[SoccerMatch] = []
        for match_key, group in match_groups.items():
            events = group["events"]
            if not events:
                continue

            # Use the GAME event as canonical (has the clean "X vs Y" title)
            # Fall back to the first event if no GAME event is present
            canonical_ev = next(
                (e for e in events
                 if _classify_bet_type(e.get("series_ticker", "")) == "MONEYLINE"),
                events[0],
            )

            event_ticker = canonical_ev.get("event_ticker", "")
            event_title = canonical_ev.get("title", "")
            series_ticker = canonical_ev.get("series_ticker", "")
            competition = _detect_competition(series_ticker)

            home_team, away_team = _parse_teams(event_title)
            kickoff_utc = self._parse_kickoff(canonical_ev)

            match = SoccerMatch(
                event_ticker=event_ticker,
                event_title=event_title,
                competition=competition,
                home_team=home_team,
                away_team=away_team,
                kickoff_utc=kickoff_utc,
                markets=group["markets"],
            )
            results.append(match)

        logger.info(
            "kalshi-soccer: %d matches, %d total markets",
            len(results),
            sum(len(m.markets) for m in results),
        )
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_events_for_series(self, series_ticker: str) -> List[Dict[str, Any]]:
        """Paginate through /events for a single series_ticker.

        Kalshi returns up to 200 events per page; we follow cursor-based
        pagination until there are no more results.
        """
        all_events: List[Dict[str, Any]] = []
        cursor: Optional[str] = None

        for page in range(50):  # hard safety cap
            params: Dict[str, Any] = {
                "series_ticker": series_ticker,
                "limit": 200,
                "status": "open",
                "with_nested_markets": True,
            }
            if cursor:
                params["cursor"] = cursor

            try:
                data = self._kc._get("/events", params=params)
            except Exception as exc:
                logger.exception(
                    "Error fetching series=%s page=%d: %s", series_ticker, page, exc
                )
                break

            events = data.get("events", [])
            all_events.extend(events)

            cursor = data.get("cursor")
            if not cursor or not events:
                break

        return all_events

    def _parse_kickoff(self, event: Dict[str, Any]) -> Optional[datetime]:
        """Extract kickoff time from event milestones or start_date."""
        # Try milestones first (array of {milestone, value})
        for milestone in event.get("milestones", []):
            if milestone.get("milestone") in ("start", "Start", "open"):
                raw = milestone.get("value")
                if raw:
                    return self._parse_iso(raw)

        # Fall back to top-level start_date
        raw = event.get("start_date") or event.get("open_time")
        if raw:
            return self._parse_iso(raw)

        return None

    @staticmethod
    def _parse_iso(s: str) -> Optional[datetime]:
        """Parse an ISO 8601 datetime string, tolerating timezone offsets."""
        try:
            # Python 3.11+ fromisoformat handles Z; older needs manual replace
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _parse_market(
        self,
        mkt: Dict[str, Any],
        bet_type: str,
        event: Dict[str, Any],
    ) -> SoccerMarket:
        """Convert a raw Kalshi market dict into a SoccerMarket dataclass."""
        market_ticker = mkt.get("ticker", "")
        market_title = mkt.get("title", "")
        yes_sub_title = mkt.get("yes_sub_title") or mkt.get("subtitle") or ""
        no_sub_title = mkt.get("no_sub_title") or ""

        # Prices: prefer *_dollars fields (already normalised); fall back to
        # raw cent-integer fields divided by 100
        yes_ask = (
            _cents_to_dollars(mkt.get("yes_ask_dollars"))
            or (mkt.get("yes_ask") / 100 if mkt.get("yes_ask") else None)
        )
        no_ask = (
            _cents_to_dollars(mkt.get("no_ask_dollars"))
            or (mkt.get("no_ask") / 100 if mkt.get("no_ask") else None)
        )
        last_price = (
            _cents_to_dollars(mkt.get("last_price_dollars"))
            or (mkt.get("last_price") / 100 if mkt.get("last_price") else None)
        )

        # Implied probability is simply the yes_ask (already 0-1 on Kalshi)
        implied_prob_yes = yes_ask if yes_ask is not None else None

        # For SPREAD / OVER_UNDER, extract the numeric line from the title
        line: Optional[float] = None
        if bet_type in ("SPREAD", "OVER_UNDER"):
            line = _parse_line(market_title) or _parse_line(yes_sub_title)

        # Parse team information from the parent event
        event_title = event.get("title", "")
        home_team, away_team = _parse_teams(event_title)

        side = _parse_side(market_title, yes_sub_title, home_team, away_team, bet_type)

        return SoccerMarket(
            market_ticker=market_ticker,
            market_title=market_title,
            bet_type=bet_type,
            yes_sub_title=yes_sub_title,
            no_sub_title=no_sub_title,
            yes_ask=yes_ask,
            no_ask=no_ask,
            last_price=last_price,
            implied_prob_yes=implied_prob_yes,
            line=line,
            side=side,
        )


# ---------------------------------------------------------------------------
# CLI entry-point for manual testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging_fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    import logging
    logging.basicConfig(level=logging.INFO, format=logging_fmt)

    client = KalshiSoccerClient()
    matches = client.fetch_match_markets()

    if not matches:
        print("No matches found.")
        sys.exit(0)

    print(f"\n{'=' * 70}")
    print(f"  Kalshi Soccer Markets — {len(matches)} match(es) found")
    print(f"{'=' * 70}\n")

    for match in sorted(matches, key=lambda m: (m.competition, m.kickoff_utc or datetime.min)):
        kickoff_str = match.kickoff_utc.strftime("%Y-%m-%d %H:%M UTC") if match.kickoff_utc else "TBD"
        print(
            f"[{match.competition}]  {match.home_team} vs {match.away_team}"
            f"  —  {kickoff_str}"
        )
        print(f"  event_ticker : {match.event_ticker}")

        # Group markets by bet type for clean display
        by_type: Dict[str, List[SoccerMarket]] = defaultdict(list)
        for mkt in match.markets:
            by_type[mkt.bet_type].append(mkt)

        for bet_type, mkts in sorted(by_type.items()):
            print(f"  {bet_type} ({len(mkts)} contract(s)):")
            for mkt in mkts:
                prob_str = f"{mkt.implied_prob_yes:.0%}" if mkt.implied_prob_yes else "N/A"
                line_str = f"  line={mkt.line}" if mkt.line is not None else ""
                side_str = f"  side={mkt.side}" if mkt.side else ""
                print(
                    f"    [{mkt.market_ticker}]  {mkt.market_title}"
                    f"  |  yes_ask=${mkt.yes_ask}  prob={prob_str}"
                    f"{line_str}{side_str}"
                )

        print()
