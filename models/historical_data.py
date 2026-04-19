"""Historical match result fetcher for model calibration.

Fetches finished match results from football-data.org and caches them
locally at football_intel/data/historical_results.json. The cache has a
24-hour TTL to avoid hammering the free-tier rate limit (10 req/min).

Supported competition codes:
  PL   → Premier League (EPL)
  BL1  → Bundesliga
  CL   → UEFA Champions League
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from football_intel.common.logging_utils import get_logger
from football_intel.ingestion.football_data import FootballDataClient

logger = get_logger(__name__)

# Path to the shared JSON cache file, relative to the project root.
# Resolved relative to this file: football_intel/models/ → football_intel/ → data/
_MODULE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _MODULE_DIR.parent
CACHE_PATH = _PROJECT_ROOT / "data" / "historical_results.json"

# How long the cache stays valid before a re-fetch is triggered (seconds).
CACHE_TTL_SECONDS = 24 * 3600

# Sleep between each API request to stay under the 10 req/min free-tier cap.
_REQUEST_SLEEP_SECONDS = 6


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    """A single finished football match."""
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    competition: str   # competition code, e.g. 'PL'
    date: datetime     # UTC kickoff datetime


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _result_to_dict(r: MatchResult) -> Dict[str, Any]:
    """Serialise a MatchResult to a JSON-safe dict."""
    d = asdict(r)
    d["date"] = r.date.isoformat()
    return d


def _dict_to_result(d: Dict[str, Any]) -> MatchResult:
    """Deserialise a MatchResult from a dict loaded from JSON."""
    date_str = d["date"]
    try:
        date = datetime.fromisoformat(date_str)
    except ValueError:
        # Fallback: strip trailing Z and parse
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return MatchResult(
        home_team=d["home_team"],
        away_team=d["away_team"],
        home_goals=int(d["home_goals"]),
        away_goals=int(d["away_goals"]),
        competition=d["competition"],
        date=date,
    )


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_is_fresh() -> bool:
    """Return True if the cache file exists and is younger than CACHE_TTL_SECONDS."""
    if not CACHE_PATH.exists():
        return False
    age = datetime.now(tz=timezone.utc).timestamp() - CACHE_PATH.stat().st_mtime
    return age < CACHE_TTL_SECONDS


def _load_cache() -> List[MatchResult]:
    """Load MatchResults from the cache file."""
    try:
        raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        results = [_dict_to_result(d) for d in raw]
        logger.info("historical_data: loaded %d results from cache (%s)", len(results), CACHE_PATH)
        return results
    except Exception as exc:  # noqa: BLE001
        logger.warning("historical_data: cache load failed (%s), will re-fetch", exc)
        return []


def _save_cache(results: List[MatchResult]) -> None:
    """Persist MatchResults to the cache file."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [_result_to_dict(r) for r in results]
    CACHE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("historical_data: cached %d results to %s", len(results), CACHE_PATH)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_match_result(match: Dict[str, Any], competition_code: str) -> Optional[MatchResult]:
    """Extract a MatchResult from a raw football-data.org match dict.

    Returns None if the match doesn't have full-time score data.
    """
    score = match.get("score", {})
    full_time = score.get("fullTime", {})

    home_goals = full_time.get("home")
    away_goals = full_time.get("away")
    if home_goals is None or away_goals is None:
        return None

    home_team = (
        match.get("homeTeam", {}).get("name")
        or match.get("homeTeam", {}).get("shortName")
        or ""
    )
    away_team = (
        match.get("awayTeam", {}).get("name")
        or match.get("awayTeam", {}).get("shortName")
        or ""
    )
    if not home_team or not away_team:
        return None

    # Parse UTC date from the match's 'utcDate' field (ISO 8601)
    raw_date = match.get("utcDate", "")
    try:
        date = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        date = datetime.now(tz=timezone.utc)

    return MatchResult(
        home_team=home_team,
        away_team=away_team,
        home_goals=int(home_goals),
        away_goals=int(away_goals),
        competition=competition_code,
        date=date,
    )


# ---------------------------------------------------------------------------
# Main fetcher class
# ---------------------------------------------------------------------------

class HistoricalDataFetcher:
    """Fetch and cache finished match results from football-data.org.

    Wraps ``FootballDataClient.fetch_matches`` with:
    - A local JSON cache (24-hour TTL)
    - Polite 6-second sleeps between API calls (free-tier: 10 req/min)
    - Graceful error handling — returns partial data on failure
    """

    def __init__(self) -> None:
        self._client = FootballDataClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_season_results(self, competition_code: str, season: int) -> List[MatchResult]:
        """Fetch all finished matches for a specific competition and season.

        Args:
            competition_code: 'PL', 'BL1', or 'CL'
            season: Year the season starts, e.g. 2024 for the 2024-25 season.
                    football-data.org interprets the 'season' query param this way.

        Returns:
            List of MatchResult objects (only matches with full-time scores).

        Note:
            The free tier can only access the current and prior season.
            Data older than ~1 year may not be available.
        """
        import datetime as dt

        # Approximate date range: Aug 1 of season year → Jul 31 the year after
        date_from = dt.date(season, 8, 1)
        date_to = dt.date(season + 1, 7, 31)

        logger.info(
            "historical_data: fetching %s season %d (%s → %s)",
            competition_code, season, date_from, date_to,
        )

        raw_matches = self._fetch_with_retry(
            competition_code,
            date_from=date_from,
            date_to=date_to,
        )

        results = []
        for m in raw_matches:
            r = _parse_match_result(m, competition_code)
            if r:
                results.append(r)

        logger.info(
            "historical_data: %s season %d → %d finished matches",
            competition_code, season, len(results),
        )
        return results

    def fetch_recent_results(
        self,
        competition_code: str,
        lookback_days: int = 365,
    ) -> List[MatchResult]:
        """Fetch recently finished matches for a single competition.

        Args:
            competition_code: 'PL', 'BL1', or 'CL'
            lookback_days: How far back to look (default 365, i.e. ~1 year).
                           The free tier's practical limit is roughly 365 days.

        Returns:
            List of MatchResult objects sorted by date ascending.
        """
        import datetime as dt

        today = dt.date.today()
        date_from = today - dt.timedelta(days=lookback_days)
        date_to = today

        logger.info(
            "historical_data: fetching %s recent results (%s → %s)",
            competition_code, date_from, date_to,
        )

        raw_matches = self._fetch_with_retry(
            competition_code,
            date_from=date_from,
            date_to=date_to,
        )

        results = []
        for m in raw_matches:
            r = _parse_match_result(m, competition_code)
            if r:
                results.append(r)

        results.sort(key=lambda r: r.date)
        logger.info(
            "historical_data: %s recent → %d finished matches",
            competition_code, len(results),
        )
        return results

    def fetch_all_competitions(
        self,
        competition_codes: Optional[List[str]] = None,
        lookback_days: int = 365,
        use_cache: bool = True,
    ) -> List[MatchResult]:
        """Fetch recent results for all (or specified) competitions.

        Results are cached to ``football_intel/data/historical_results.json``
        with a 24-hour TTL.

        Args:
            competition_codes: Which competitions to fetch. Defaults to
                               ['PL', 'BL1', 'CL'].
            lookback_days: How far back to look for each competition.
            use_cache: If True (default), load from cache if it's fresh.

        Returns:
            Combined list of MatchResult objects across all competitions.
        """
        if use_cache and _cache_is_fresh():
            logger.info("historical_data: cache is fresh, skipping API fetch")
            return _load_cache()

        codes = competition_codes or ["PL", "BL1", "CL"]
        all_results: List[MatchResult] = []

        for i, code in enumerate(codes):
            try:
                results = self.fetch_recent_results(code, lookback_days=lookback_days)
                all_results.extend(results)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "historical_data: error fetching %s: %s", code, exc
                )

            # Respect free-tier rate limit — sleep between competitions
            if i < len(codes) - 1:
                logger.debug("historical_data: sleeping %ds (rate limit)", _REQUEST_SLEEP_SECONDS)
                time.sleep(_REQUEST_SLEEP_SECONDS)

        # Persist to cache
        _save_cache(all_results)
        return all_results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_with_retry(
        self,
        competition_code: str,
        date_from: "dt.date",
        date_to: "dt.date",
        retries: int = 2,
    ) -> List[Dict[str, Any]]:
        """Fetch finished matches with simple retry logic."""
        import datetime as dt  # noqa: F811

        for attempt in range(retries + 1):
            try:
                raw = self._client.fetch_matches(
                    league_code=competition_code,
                    date_from=date_from,
                    date_to=date_to,
                    status="FINISHED",
                )
                return raw
            except Exception as exc:
                if attempt < retries:
                    wait = _REQUEST_SLEEP_SECONDS * (attempt + 1)
                    logger.warning(
                        "historical_data: attempt %d failed for %s (%s), retrying in %ds",
                        attempt + 1, competition_code, exc, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.exception(
                        "historical_data: all retries exhausted for %s: %s",
                        competition_code, exc,
                    )
                    return []
        return []  # unreachable but satisfies type checker


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

def load_historical_results(
    competition_codes: Optional[List[str]] = None,
    lookback_days: int = 365,
    use_cache: bool = True,
) -> List[MatchResult]:
    """Convenience wrapper: fetch (or load from cache) historical match results.

    This is the primary entry point used by the calibrated model.

    Args:
        competition_codes: Defaults to ['PL', 'BL1', 'CL'].
        lookback_days: How far back to look (max ~365 on free tier).
        use_cache: If True, use the 24h JSON cache.

    Returns:
        List of MatchResult objects ready for calibration.
    """
    fetcher = HistoricalDataFetcher()
    return fetcher.fetch_all_competitions(
        competition_codes=competition_codes,
        lookback_days=lookback_days,
        use_cache=use_cache,
    )
