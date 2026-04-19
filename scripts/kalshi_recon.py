"""Kalshi Soccer Reconnaissance Script.

Fetches all open soccer/football-related events from the Kalshi API,
including nested markets and milestones, then classifies each market
into a bet type and outputs a structured JSON report.

Usage:
    cd ~/.openclaw/workspace
    python3 -m football_intel.scripts.kalshi_recon
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from football_intel.ingestion.kalshi import _load_private_key, _sign_request
from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger

import requests
from urllib.parse import urlparse

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOCCER_KEYWORDS = [
    "soccer",
    "football",
    "premier league",
    "epl",
    "la liga",
    "bundesliga",
    "serie a",
    "ligue 1",
    "champions league",
    "ucl",
    "world cup",
    "fifa",
    "mls",
    "europa league",
    "uel",
    "fa cup",
    "copa del rey",
    "dfb pokal",
    "coppa italia",
    "coupe de france",
    "nations league",
    "euro",
    "concacaf",
    "conmebol",
    "copa america",
    "afcon",
]

BET_TYPE_PATTERNS: List[tuple[str, list[str]]] = [
    # Order matters — more specific patterns first
    ("FUTURES", [
        r"\bchampion\b",
        r"\bwinner of\b",
        r"\bballon d.or\b",
        r"\bgolden boot\b",
        r"\brelegation\b",
        r"\btitle\b",
        r"\bleague winner\b",
    ]),
    ("SERIES", [
        r"\badvance\b",
        r"\bqualif(y|ied|ication)\b",
        r"\bround of \d+\b",
        r"\bsemifinal\b",
        r"\bfinal\b",
        r"\bnext round\b",
        r"\bout of\b",
    ]),
    ("PLAYER_PROP", [
        r"\bgoals? scored\b",
        r"\bassists?\b",
        r"\bcards?\b",
        r"\bfirst goalscorer\b",
        r"\banytime scorer\b",
        r"\bhat.trick\b",
        r"\bclean sheet\b",
        r"\bsave\b",
    ]),
    ("OVER_UNDER", [
        r"\bover\b",
        r"\bunder\b",
        r"\btotal goals?\b",
        r"\btotal score\b",
        r"\bboth teams? to score\b",
        r"\bbtts\b",
    ]),
    ("SPREAD", [
        r"\bmargin\b",
        r"\bby more than\b",
        r"\bby at least\b",
        r"\bspread\b",
        r"\bhandicap\b",
    ]),
    ("MONEYLINE", [
        r"\bwin\b",
        r"\bwinner\b",
        r"\bto win\b",
        r"\bdraw\b",
        r"\bmoneyline\b",
        r"\bmatch result\b",
    ]),
]


# ---------------------------------------------------------------------------
# Auth helpers (reused from kalshi.py pattern)
# ---------------------------------------------------------------------------

class KalshiReconClient:
    """Minimal Kalshi API client for reconnaissance — no WebSocket, no caching."""

    def __init__(self) -> None:
        cfg = load_config().kalshi
        self.base_url = cfg.base_url.rstrip("/")
        self.key_id = cfg.key_id
        self.private_key = _load_private_key(cfg.private_key_path)
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _auth_headers(self, method: str, path: str) -> Dict[str, str]:
        import datetime as dt
        timestamp_ms = str(int(dt.datetime.now().timestamp() * 1000))
        full_path = urlparse(self.base_url + path).path
        signature = _sign_request(self.private_key, timestamp_ms, method, full_path)
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = self._auth_headers("GET", path)
        logger.debug("GET %s params=%s", url, params)
        resp = self.session.get(url, headers=headers, params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def fetch_all_open_events(self) -> List[Dict[str, Any]]:
        """Paginate through /events to get all open events with nested markets and milestones."""
        all_events: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        page = 0

        while True:
            page += 1
            params: Dict[str, Any] = {
                "status": "open",
                "with_nested_markets": "true",
                "with_milestones": "true",
                "limit": 200,
            }
            if cursor:
                params["cursor"] = cursor

            logger.info("Fetching events page %d (cursor=%s)…", page, cursor or "start")
            data = self._get("/events", params=params)

            events = data.get("events", [])
            all_events.extend(events)

            cursor = data.get("cursor")
            if not cursor or not events:
                break

            # Safety: stop after 50 pages (~10 000 events)
            if page >= 50:
                logger.warning("Reached page limit (50). Stopping pagination.")
                break

        logger.info("Fetched %d total open events across %d pages.", len(all_events), page)
        return all_events


# ---------------------------------------------------------------------------
# Soccer filter
# ---------------------------------------------------------------------------

def _text_contains_soccer(text: str) -> bool:
    """Return True if the text contains any soccer-related keyword."""
    lower = text.lower()
    return any(kw in lower for kw in SOCCER_KEYWORDS)


def is_soccer_event(event: Dict[str, Any]) -> bool:
    """Determine if a Kalshi event is soccer/football related."""
    category = (event.get("category") or "").lower()
    title = event.get("title") or ""
    ticker = event.get("event_ticker") or ""
    series = event.get("series_ticker") or ""

    # Check title, ticker, series_ticker for keywords
    if _text_contains_soccer(title) or _text_contains_soccer(ticker) or _text_contains_soccer(series):
        return True

    # Check milestone types
    for milestone in (event.get("milestones") or []):
        milestone_type = (milestone.get("type") or "").lower()
        milestone_title = (milestone.get("title") or "").lower()
        if "soccer" in milestone_type or "football" in milestone_type:
            return True
        if _text_contains_soccer(milestone_title):
            return True

    # Check nested markets for soccer keywords
    for market in (event.get("markets") or []):
        market_title = market.get("title") or ""
        yes_sub = market.get("yes_sub_title") or ""
        no_sub = market.get("no_sub_title") or ""
        if any(_text_contains_soccer(t) for t in [market_title, yes_sub, no_sub]):
            return True

    return False


# ---------------------------------------------------------------------------
# Bet type classifier
# ---------------------------------------------------------------------------

def classify_bet_type(market: Dict[str, Any]) -> str:
    """Classify a market into a bet type based on title/subtitle text patterns."""
    # Combine all text fields for matching
    text_parts = [
        market.get("title") or "",
        market.get("yes_sub_title") or "",
        market.get("no_sub_title") or "",
        market.get("market_type") or "",
        market.get("subtitle") or "",
    ]
    combined = " ".join(text_parts).lower()

    for bet_type, patterns in BET_TYPE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return bet_type

    return "OTHER"


# ---------------------------------------------------------------------------
# Market normaliser
# ---------------------------------------------------------------------------

def _cents_to_dollars(val: Any) -> Optional[float]:
    """Convert Kalshi cents integer to dollars float, or return None."""
    if val is None:
        return None
    try:
        return round(int(val) / 100.0, 4)
    except (TypeError, ValueError):
        return None


def normalise_market(market: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the fields we care about from a raw market dict."""
    return {
        "ticker": market.get("ticker"),
        "title": market.get("title"),
        "market_type": market.get("market_type"),
        "yes_sub_title": market.get("yes_sub_title"),
        "no_sub_title": market.get("no_sub_title"),
        "status": market.get("status"),
        "yes_ask_dollars": _cents_to_dollars(market.get("yes_ask")),
        "no_ask_dollars": _cents_to_dollars(market.get("no_ask")),
        "last_price_dollars": _cents_to_dollars(market.get("last_price")),
        "bet_type": classify_bet_type(market),
    }


def normalise_milestone(milestone: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": milestone.get("type"),
        "title": milestone.get("title"),
        "start_date": milestone.get("start_date"),
    }


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def build_report(soccer_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a structured JSON report from filtered soccer events."""
    bet_type_counts: Dict[str, int] = {}
    processed_events = []

    for event in soccer_events:
        markets_raw = event.get("markets") or []
        milestones_raw = event.get("milestones") or []

        classified_markets = [normalise_market(m) for m in markets_raw]
        classified_milestones = [normalise_milestone(ms) for ms in milestones_raw]

        # Tally bet types
        for m in classified_markets:
            bt = m["bet_type"]
            bet_type_counts[bt] = bet_type_counts.get(bt, 0) + 1

        processed_events.append({
            "event_ticker": event.get("event_ticker"),
            "title": event.get("title"),
            "series_ticker": event.get("series_ticker"),
            "category": event.get("category"),
            "status": event.get("status"),
            "markets": classified_markets,
            "milestones": classified_milestones,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_events": len(processed_events),
            "total_markets": sum(bet_type_counts.values()),
            "markets_by_bet_type": bet_type_counts,
        },
        "events": processed_events,
    }


# ---------------------------------------------------------------------------
# Human-readable summary printer
# ---------------------------------------------------------------------------

def print_summary(report: Dict[str, Any]) -> None:
    summary = report["summary"]
    events = report["events"]

    print("\n" + "=" * 70)
    print("  KALSHI SOCCER MARKET RECONNAISSANCE REPORT")
    print(f"  Generated: {report['generated_at']}")
    print("=" * 70)
    print(f"\n📊 SUMMARY")
    print(f"   Events found:   {summary['total_events']}")
    print(f"   Total markets:  {summary['total_markets']}")
    print("\n   Markets by bet type:")
    for bt, count in sorted(summary["markets_by_bet_type"].items(), key=lambda x: -x[1]):
        print(f"     {bt:<15} {count:>4}")

    print(f"\n{'─' * 70}")
    print("  EVENTS DETAIL")
    print(f"{'─' * 70}\n")

    for ev in events:
        print(f"🏟  {ev['title'] or ev['event_ticker']}")
        print(f"    Ticker:   {ev['event_ticker']}")
        print(f"    Series:   {ev['series_ticker']}")
        print(f"    Category: {ev['category']}")

        if ev["milestones"]:
            print(f"    Milestones ({len(ev['milestones'])}):")
            for ms in ev["milestones"]:
                print(f"      · [{ms['type']}] {ms['title']}  start={ms['start_date']}")

        if ev["markets"]:
            print(f"    Markets ({len(ev['markets'])}):")
            for m in ev["markets"]:
                price_str = (
                    f"yes={m['yes_ask_dollars']}  no={m['no_ask_dollars']}  last={m['last_price_dollars']}"
                    if any(v is not None for v in [m["yes_ask_dollars"], m["no_ask_dollars"], m["last_price_dollars"]])
                    else "no price data"
                )
                print(f"      [{m['bet_type']:<12}] {m['ticker']}  status={m['status']}")
                print(f"                     yes: {m['yes_sub_title']}  |  no: {m['no_sub_title']}")
                print(f"                     {price_str}")
        else:
            print("    Markets: none")

        print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    output_path = Path(__file__).resolve().parents[2] / "data" / "kalshi_soccer_recon.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("🔍 Connecting to Kalshi API…")
    client = KalshiReconClient()

    print("📡 Fetching all open events…")
    all_events = client.fetch_all_open_events()
    print(f"   Total open events: {len(all_events)}")

    print("⚽ Filtering for soccer/football events…")
    soccer_events = [e for e in all_events if is_soccer_event(e)]
    print(f"   Soccer events found: {len(soccer_events)}")

    if not soccer_events:
        print("\n⚠️  No soccer events found. This may be expected on the demo API.")
        print("   Check config.yaml: kalshi.base_url is currently set to the demo endpoint.")
        print(f"   Current base_url: {client.base_url}")

    print("📝 Building report…")
    report = build_report(soccer_events)

    print_summary(report)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Full JSON report saved to: {output_path}")


if __name__ == "__main__":
    main()
