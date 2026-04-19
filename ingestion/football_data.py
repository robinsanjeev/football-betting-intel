"""Client for football-data.org with incremental updates.

Focuses on top-tier European leagues and supports incremental fetching of
fixtures/results based on last-seen match date or ID.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

import json
from pathlib import Path

import requests

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)


class FootballDataClient:
    def __init__(self) -> None:
        cfg = load_config().football_data
        self.base_url = cfg.base_url.rstrip("/")
        self.api_key = cfg.api_key
        self.leagues = cfg.leagues
        self.max_leagues_per_run = cfg.max_leagues_per_run
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": self.api_key})

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.debug("GET %s params=%s", url, params)
        resp = self.session.get(url, params=params or {}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def fetch_matches(
        self,
        league_code: str,
        date_from: Optional[dt.date] = None,
        date_to: Optional[dt.date] = None,
        status: str = "SCHEDULED,FINISHED,IN_PLAY,PAUSED",
    ) -> List[Dict[str, Any]]:
        """Fetch matches for a league within an optional date range.

        Use this with an incremental strategy: call with date_from set to the
        last date we saw in the cache to avoid re-pulling old data.
        """

        params: Dict[str, Any] = {"status": status}
        if date_from:
            params["dateFrom"] = date_from.isoformat()
        if date_to:
            params["dateTo"] = date_to.isoformat()

        data = self._get(f"competitions/{league_code}/matches", params=params)
        return data.get("matches", [])

    def fetch_all_leagues_incremental(
        self,
        last_seen_date: Optional[dt.date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch matches incrementally for all configured leagues.

        If last_seen_date is provided, we only fetch matches from that date
        onward to respect free-tier limits.
        """

        all_matches: List[Dict[str, Any]] = []
        today = dt.date.today()
        date_from = last_seen_date or today
        date_to = today + dt.timedelta(days=7)

        # If leagues contains "ALL" (or is empty), expand to all free-tier competitions.
        if not self.leagues or "ALL" in self.leagues:
            try:
                data = self._get("competitions")
                comps = data.get("competitions", [])
                league_codes = [
                    c["code"]
                    for c in comps
                    if c.get("plan") == "TIER_ONE" and c.get("code")
                ]
                logger.info(
                    "football-data.org: resolved %d TIER_ONE competitions", len(league_codes)
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Error listing competitions: %s", exc)
                league_codes = []
        else:
            league_codes = list(self.leagues)

        # Rotate through leagues over time to respect API rate limits.
        # We keep simple state in state/football_data_state.json (offset + last league list).
        max_leagues = max(1, self.max_leagues_per_run or 1)
        if league_codes:
            state_path = Path("state/football_data_state.json")
            offset = 0
            if state_path.exists():
                try:
                    st = json.loads(state_path.read_text())
                    offset = int(st.get("offset", 0))
                except Exception:  # noqa: BLE001
                    offset = 0

            n = min(max_leagues, len(league_codes))
            ordered = league_codes[offset : offset + n]
            if len(ordered) < n:
                ordered += league_codes[: n - len(ordered)]

            next_offset = (offset + n) % len(league_codes)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                state_path.write_text(
                    json.dumps({"offset": next_offset, "league_count": len(league_codes)}, indent=2)
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not write football_data_state.json: %s", exc)

            target_leagues = ordered
        else:
            target_leagues = []

        for league in target_leagues:
            try:
                matches = self.fetch_matches(league, date_from=date_from, date_to=date_to)
                all_matches.extend(matches)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Error fetching matches for league %s: %s", league, exc)

        return all_matches
