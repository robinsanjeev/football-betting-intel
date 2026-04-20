"""Football Intel FastAPI backend.

Run with:
    cd ~/.openclaw/workspace
    python3 -m football_intel.api.main

Or:
    uvicorn football_intel.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from football_intel.api.cache import SignalCache
from football_intel.api.models import (
    AccuracyResponse,
    AdaptiveParamsResponse,
    AdaptiveReportResponse,
    CalibrationBucket,
    CalibrationPoint,
    CumulativePnLPoint,
    FirstHalfProbs,
    GoalDistributionEntry,
    GroupStats,
    HealthResponse,
    MatchInsightResponse,
    ModelInsightsResponse,
    PerformanceResponse,
    Prob1X2,
    ProbOverUnder,
    RetuneResponse,
    RollingWinRatePoint,
    ScorelineEntry,
    SignalResponse,
    SignalsListResponse,
    TeamStrengthData,
    TradeResponse,
    TradesListResponse,
    WeeklyROIPoint,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Football Intel API",
    description="Betting dashboard backend — signals, trades, and performance metrics.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory signal cache (shared across requests)
# ---------------------------------------------------------------------------

_signal_cache = SignalCache(ttl_seconds=900)  # 15 minutes

# ---------------------------------------------------------------------------
# Team crest helpers
# ---------------------------------------------------------------------------

_crests_cache: Optional[Dict[str, str]] = None


def _load_crests() -> Dict[str, str]:
    """Load team crest mappings from the JSON cache file."""
    global _crests_cache
    if _crests_cache is not None:
        return _crests_cache
    import json
    from pathlib import Path
    crest_path = Path("football_intel/data/team_crests.json")
    if crest_path.exists():
        with crest_path.open() as f:
            _crests_cache = json.load(f)
    else:
        _crests_cache = {}
    return _crests_cache


def _find_crest(crests: Dict[str, str], team_name: str) -> str:
    """Find a team's crest URL by name, with fuzzy fallback."""
    if not team_name:
        return ""
    # Exact match
    if team_name in crests:
        return crests[team_name]
    # Try with FC suffix
    if f"{team_name} FC" in crests:
        return crests[f"{team_name} FC"]
    # Case-insensitive search
    lower = team_name.lower()
    for key, url in crests.items():
        if key.lower() == lower:
            return url
    # Substring match — require at least 4 chars to avoid false positives
    # (e.g. "MUN" matching "Munich")
    if len(lower) >= 4:
        for key, url in crests.items():
            kl = key.lower()
            if len(kl) >= 4 and (lower in kl or kl in lower):
                return url
    return ""


# ---------------------------------------------------------------------------
# DB path helper
# ---------------------------------------------------------------------------

def _get_db_path() -> str:
    """Return the SQLite DB path from env var or default."""
    return os.environ.get(
        "FOOTBALL_INTEL_DB",
        "football_intel/data/football_intel.db",
    )


def _get_db_connection() -> sqlite3.Connection:
    """Open a read/write SQLite connection to the trades DB."""
    db_path = _get_db_path()
    # Ensure the parent directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_trades_table(conn: sqlite3.Connection) -> None:
    """Create the trades table if it doesn't exist yet."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            match TEXT NOT NULL,
            side TEXT NOT NULL,
            stake REAL NOT NULL,
            odds REAL NOT NULL,
            result TEXT NOT NULL DEFAULT 'PENDING',
            pnl REAL NOT NULL DEFAULT 0.0
        )
        """
    )
    conn.commit()


def _ensure_signal_history_table(conn: sqlite3.Connection) -> None:
    """Create the signal_history table and indexes if they do not exist."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT NOT NULL,
            event_ticker TEXT NOT NULL,
            market_ticker TEXT NOT NULL UNIQUE,
            match_title TEXT NOT NULL,
            competition TEXT NOT NULL,
            bet_type TEXT NOT NULL,
            description TEXT NOT NULL,
            model_prob REAL NOT NULL,
            kalshi_implied_prob REAL NOT NULL,
            edge REAL NOT NULL,
            confidence TEXT NOT NULL,
            reasoning TEXT NOT NULL,
            kalshi_url TEXT NOT NULL,
            entry_cents INTEGER NOT NULL,
            upside_cents INTEGER NOT NULL,
            score INTEGER NOT NULL,
            home_crest TEXT,
            away_crest TEXT,
            league_emblem TEXT,
            outcome TEXT DEFAULT 'PENDING',
            actual_pnl REAL DEFAULT 0.0
        );

        CREATE INDEX IF NOT EXISTS idx_signal_history_event_ticker
        ON signal_history (event_ticker);

        CREATE INDEX IF NOT EXISTS idx_signal_history_generated_at
        ON signal_history (generated_at);
        """
    )
    conn.commit()


def _upsert_signal_history(
    conn: sqlite3.Connection,
    signal_dicts: List[Dict[str, Any]],
    generated_at: datetime,
) -> None:
    """Insert or update the latest batch of generated signals."""
    if not signal_dicts:
        return

    generated_at_iso = generated_at.isoformat()
    rows = [
        (
            generated_at_iso,
            signal["event_ticker"],
            signal["market_ticker"],
            signal["match_title"],
            signal["competition"],
            signal["bet_type"],
            signal["description"],
            signal["model_prob"],
            signal["kalshi_implied_prob"],
            signal["edge"],
            signal["confidence"],
            signal["reasoning"],
            signal["kalshi_url"],
            signal["entry_cents"],
            signal["upside_cents"],
            signal["score"],
            signal.get("home_crest") or None,
            signal.get("away_crest") or None,
            signal.get("league_emblem") or None,
        )
        for signal in signal_dicts
    ]

    conn.executemany(
        """
        INSERT INTO signal_history (
            generated_at,
            event_ticker,
            market_ticker,
            match_title,
            competition,
            bet_type,
            description,
            model_prob,
            kalshi_implied_prob,
            edge,
            confidence,
            reasoning,
            kalshi_url,
            entry_cents,
            upside_cents,
            score,
            home_crest,
            away_crest,
            league_emblem
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(market_ticker) DO UPDATE SET
            generated_at = excluded.generated_at,
            event_ticker = excluded.event_ticker,
            match_title = excluded.match_title,
            competition = excluded.competition,
            bet_type = excluded.bet_type,
            description = excluded.description,
            model_prob = excluded.model_prob,
            kalshi_implied_prob = excluded.kalshi_implied_prob,
            edge = excluded.edge,
            confidence = excluded.confidence,
            reasoning = excluded.reasoning,
            kalshi_url = excluded.kalshi_url,
            entry_cents = excluded.entry_cents,
            upside_cents = excluded.upside_cents,
            score = excluded.score,
            home_crest = excluded.home_crest,
            away_crest = excluded.away_crest,
            league_emblem = excluded.league_emblem
        """,
        rows,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Pipeline runner (generates live signals)
# ---------------------------------------------------------------------------

def _run_pipeline() -> tuple[List[Dict[str, Any]], int]:
    """Run the full prediction pipeline and return (signals_dicts, total_matches).

    Returns:
        signals_dicts: list of raw signal dicts (from BettingSignal dataclasses)
        total_matches: number of Kalshi matches scanned
    """
    from football_intel.models.historical_data import load_historical_results
    from football_intel.models.calibrated_poisson import CalibratedPoissonModel
    from football_intel.ingestion.kalshi_soccer import KalshiSoccerClient
    from football_intel.strategy.signal_generator import SignalGenerator

    # Step 1: Load historical data (24-hour file cache built in)
    results = load_historical_results()

    # Step 2: Calibrate model
    model = CalibratedPoissonModel()
    model.calibrate(results)

    # Step 3: Fetch Kalshi soccer markets
    ks_client = KalshiSoccerClient()
    matches = ks_client.fetch_match_markets()
    total_matches = len(matches)

    # Step 4: Generate signals
    generator = SignalGenerator(model)
    signals = generator.generate_signals(matches, min_edge=0.05)

    # Load team crests
    crests = _load_crests()

    # League emblem mapping
    league_emblems = {
        "EPL": "https://crests.football-data.org/PL.png",
        "Bundesliga": "https://crests.football-data.org/BL1.png",
        "UCL": "https://crests.football-data.org/CL.png",
    }

    # Convert BettingSignal dataclasses to dicts
    signal_dicts = []
    for i, sig in enumerate(signals, start=1):
        entry_cents = int(round(sig.kalshi_implied_prob * 100))
        upside_cents = 100 - entry_cents
        # Score = probability-adjusted: edge * model confidence * 100
        # High-prob + high-edge = high score; low-prob longshots score lower
        score = int(min(sig.edge * sig.model_prob * 400, 100))

        # Resolve team crests from match_title ("Home vs Away")
        parts = sig.match_title.split(" vs ")
        home_name = parts[0].strip() if len(parts) >= 2 else sig.match_title
        away_name = parts[1].strip() if len(parts) >= 2 else ""
        home_crest = _find_crest(crests, home_name)
        away_crest = _find_crest(crests, away_name)
        league_emblem = league_emblems.get(sig.competition, "")

        signal_dicts.append({
            "id": i,
            "event_ticker": sig.event_ticker,
            "match_title": sig.match_title,
            "competition": sig.competition,
            "bet_type": sig.bet_type,
            "description": sig.description,
            "market_ticker": sig.market_ticker,
            "model_prob": round(sig.model_prob, 4),
            "kalshi_implied_prob": round(sig.kalshi_implied_prob, 4),
            "edge": round(sig.edge, 4),
            "ev_per_dollar": round(sig.ev_per_dollar, 4),
            "confidence": sig.confidence,
            "reasoning": sig.reasoning,
            "kalshi_url": sig.kalshi_url,
            "entry_cents": entry_cents,
            "upside_cents": upside_cents,
            "score": score,
            "home_crest": home_crest,
            "away_crest": away_crest,
            "league_emblem": league_emblem,
        })

    return signal_dicts, total_matches


def _get_signals_from_pipeline() -> tuple[List[Dict[str, Any]], int, datetime]:
    """Run the signal pipeline and return signals with a shared batch timestamp."""
    signal_dicts, total_matches = _run_pipeline()
    generated_at = datetime.now(tz=timezone.utc)
    return signal_dicts, total_matches, generated_at


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Simple health check."""
    db_path = _get_db_path()
    db_accessible = False
    try:
        conn = _get_db_connection()
        _ensure_trades_table(conn)
        _ensure_signal_history_table(conn)
        conn.close()
        db_accessible = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        db_path=db_path,
        db_accessible=db_accessible,
        cache_stale=_signal_cache.is_stale(),
        signals_cached=len(_signal_cache.get() or []),
    )


@app.get("/api/signals/active", response_model=SignalsListResponse)
def signals_active() -> SignalsListResponse:
    """Return current live betting signals.

    Runs the full pipeline on first call or after cache expiry (15 min TTL).
    Signals are sorted by EV per dollar descending.
    """
    # Try to serve from cache
    cached = _signal_cache.get()
    if cached is not None:
        generated_at = _signal_cache.generated_at
        return SignalsListResponse(
            signals=[SignalResponse(**s) for s in cached],
            generated_at=generated_at.isoformat() if generated_at else datetime.now(tz=timezone.utc).isoformat(),
            total_matches_scanned=0,  # not stored in cache but cached means fresh
        )

    # Cache miss — run the pipeline
    try:
        signal_dicts, total_matches, generated_at = _get_signals_from_pipeline()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline error: {exc}",
        ) from exc

    conn = _get_db_connection()
    try:
        _ensure_signal_history_table(conn)
        _upsert_signal_history(conn, signal_dicts, generated_at)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Signal history persistence error: {exc}",
        ) from exc
    finally:
        conn.close()

    _signal_cache.set(signal_dicts, generated_at)

    return SignalsListResponse(
        signals=[SignalResponse(**s) for s in signal_dicts],
        generated_at=generated_at.isoformat(),
        total_matches_scanned=total_matches,
    )


@app.get("/api/trades", response_model=TradesListResponse)
def list_trades(
    status: Optional[str] = Query(default=None, description="Filter by result: PENDING, WIN, LOSE"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> TradesListResponse:
    """Return trades from the ledger.

    Optionally filter by `status` (PENDING / WIN / LOSE).
    Supports `limit` and `offset` for pagination.
    """
    conn = _get_db_connection()
    try:
        _ensure_trades_table(conn)

        # Build query dynamically based on optional status filter
        where_clause = ""
        params: list = []
        if status:
            status_upper = status.upper()
            if status_upper not in ("PENDING", "WIN", "LOSE"):
                raise HTTPException(
                    status_code=400,
                    detail="status must be one of: PENDING, WIN, LOSE",
                )
            where_clause = "WHERE result = ?"
            params.append(status_upper)

        # Count totals (ignoring pagination)
        cur = conn.execute(
            f"SELECT COUNT(*) FROM trades {where_clause}", params
        )
        total_filtered = cur.fetchone()[0]

        cur = conn.execute("SELECT COUNT(*) FROM trades WHERE result = 'PENDING'")
        pending_count = cur.fetchone()[0]

        cur = conn.execute("SELECT COUNT(*) FROM trades WHERE result != 'PENDING'")
        settled_count = cur.fetchone()[0]

        # Fetch paginated rows
        cur = conn.execute(
            f"SELECT id, timestamp, match, side, stake, odds, result, pnl "
            f"FROM trades {where_clause} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    trades: List[TradeResponse] = []
    for row in rows:
        odds = row["odds"]
        implied_prob = round(1.0 / odds, 4) if odds and odds > 0 else 0.0
        trades.append(
            TradeResponse(
                id=row["id"],
                timestamp=row["timestamp"],
                match=row["match"],
                side=row["side"],
                stake=row["stake"],
                odds=row["odds"],
                implied_prob=implied_prob,
                result=row["result"],
                pnl=row["pnl"],
            )
        )

    return TradesListResponse(
        trades=trades,
        total=total_filtered,
        pending=pending_count,
        settled=settled_count,
    )


@app.get("/api/performance", response_model=PerformanceResponse)
def performance() -> PerformanceResponse:
    """Return aggregated performance metrics for all trades."""
    conn = _get_db_connection()
    try:
        _ensure_trades_table(conn)
        cur = conn.execute(
            "SELECT id, timestamp, match, side, stake, odds, result, pnl "
            "FROM trades ORDER BY id ASC"
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return PerformanceResponse(
            total_trades=0,
            settled_trades=0,
            pending_trades=0,
            win_rate=0.0,
            roi=0.0,
            total_pnl=0.0,
            max_drawdown=0.0,
            total_staked=0.0,
            cumulative_pnl=[],
            weekly_roi=[],
            win_loss_counts={"WIN": 0, "LOSE": 0, "PENDING": 0},
        )

    total_trades = len(rows)
    pending_trades = sum(1 for r in rows if r["result"] == "PENDING")
    settled_trades = total_trades - pending_trades

    total_staked = sum(r["stake"] for r in rows)
    total_pnl = sum(r["pnl"] for r in rows)

    wins = sum(1 for r in rows if r["result"] == "WIN")
    losses = sum(1 for r in rows if r["result"] == "LOSE")

    win_rate = (wins / settled_trades) if settled_trades > 0 else 0.0
    roi = (total_pnl / total_staked) if total_staked > 0 else 0.0

    # Max drawdown (equity curve)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in rows:
        equity += r["pnl"]
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)

    # Cumulative PnL by date
    pnl_by_date: Dict[str, float] = {}
    for r in rows:
        date_str = r["timestamp"][:10]  # "YYYY-MM-DD"
        pnl_by_date[date_str] = pnl_by_date.get(date_str, 0.0) + r["pnl"]

    cumulative_pnl: List[CumulativePnLPoint] = []
    running = 0.0
    for date_str in sorted(pnl_by_date):
        running += pnl_by_date[date_str]
        cumulative_pnl.append(CumulativePnLPoint(date=date_str, pnl=round(running, 4)))

    # Weekly ROI
    weekly_staked: Dict[str, float] = defaultdict(float)
    weekly_pnl: Dict[str, float] = defaultdict(float)
    weekly_trades: Dict[str, int] = defaultdict(int)
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["timestamp"])
            iso_year, iso_week, _ = dt.isocalendar()
            week_key = f"{iso_year}-W{iso_week:02d}"
        except (ValueError, TypeError):
            continue
        weekly_staked[week_key] += r["stake"]
        weekly_pnl[week_key] += r["pnl"]
        weekly_trades[week_key] += 1

    weekly_roi: List[WeeklyROIPoint] = []
    for week_key in sorted(weekly_staked):
        staked = weekly_staked[week_key]
        roi_w = (weekly_pnl[week_key] / staked) if staked > 0 else 0.0
        weekly_roi.append(
            WeeklyROIPoint(
                week=week_key,
                roi=round(roi_w, 4),
                trades=weekly_trades[week_key],
            )
        )

    win_loss_counts = {"WIN": wins, "LOSE": losses, "PENDING": pending_trades}

    return PerformanceResponse(
        total_trades=total_trades,
        settled_trades=settled_trades,
        pending_trades=pending_trades,
        win_rate=round(win_rate, 4),
        roi=round(roi, 4),
        total_pnl=round(total_pnl, 4),
        max_drawdown=round(max_dd, 4),
        total_staked=round(total_staked, 4),
        cumulative_pnl=cumulative_pnl,
        weekly_roi=weekly_roi,
        win_loss_counts=win_loss_counts,
    )


@app.get("/api/accuracy", response_model=AccuracyResponse)
def accuracy() -> AccuracyResponse:
    """Return model accuracy / calibration data for settled trades.

    Uses the model_prob stored at bet time (derived from odds) as the
    predicted probability bucket.  Since we store implied_prob (1/odds) as
    the Kalshi price, not the model probability, calibration is approximate.
    """
    conn = _get_db_connection()
    try:
        _ensure_trades_table(conn)
        cur = conn.execute(
            "SELECT id, odds, result FROM trades WHERE result != 'PENDING' ORDER BY id ASC"
        )
        settled_rows = cur.fetchall()

        cur2 = conn.execute("SELECT COUNT(*) FROM trades")
        total_count = cur2.fetchone()[0]
    finally:
        conn.close()

    total_settled = len(settled_rows)

    # Build calibration buckets (0-10%, 10-20%, … 90-100%)
    bucket_labels = [f"{i*10}-{(i+1)*10}%" for i in range(10)]
    bucket_midpoints = [i * 0.10 + 0.05 for i in range(10)]
    bucket_wins: Dict[int, int] = {i: 0 for i in range(10)}
    bucket_counts: Dict[int, int] = {i: 0 for i in range(10)}

    # Use Kalshi implied probability (1/odds) as stand-in for predicted prob
    # bucket index = int(implied_prob * 10), clamped to [0, 9]
    for row in settled_rows:
        odds = row["odds"]
        if not odds or odds <= 0:
            continue
        implied_prob = 1.0 / odds
        bucket_idx = min(int(implied_prob * 10), 9)
        bucket_counts[bucket_idx] += 1
        if row["result"] == "WIN":
            bucket_wins[bucket_idx] += 1

    calibration: List[CalibrationBucket] = []
    for i in range(10):
        count = bucket_counts[i]
        if count > 0:
            actual_win_rate: Optional[float] = round(bucket_wins[i] / count, 4)
        else:
            actual_win_rate = None
        calibration.append(
            CalibrationBucket(
                bucket=bucket_labels[i],
                predicted_prob=bucket_midpoints[i],
                actual_win_rate=actual_win_rate,
                count=count,
            )
        )

    # Rolling 10-trade win rate for settled trades
    rolling_win_rate: List[RollingWinRatePoint] = []
    win_history: List[int] = []  # 1 for win, 0 for lose
    for idx, row in enumerate(settled_rows, start=1):
        win_history.append(1 if row["result"] == "WIN" else 0)
        if len(win_history) >= 10:
            rolling = round(sum(win_history[-10:]) / 10, 4)
        else:
            rolling = None
        rolling_win_rate.append(
            RollingWinRatePoint(
                trade_number=idx,
                rolling_10_win_rate=rolling,
            )
        )

    if total_settled == 0:
        msg = "Not enough settled trades for accuracy metrics yet. Check back after matches complete."
    elif total_settled < 10:
        msg = f"{total_settled} trade(s) settled — rolling win rate needs at least 10."
    else:
        msg = f"Accuracy based on {total_settled} settled trade(s)."

    return AccuracyResponse(
        calibration=calibration,
        rolling_win_rate=rolling_win_rate,
        total_settled=total_settled,
        message=msg,
    )


@app.get("/api/signals/history")
def signals_history(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    competition: Optional[str] = Query(None),
    bet_type: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
):
    """Return all historical signals from signal_history table."""
    conn = _get_db_connection()
    try:
        _ensure_signal_history_table(conn)
        _ensure_trades_table(conn)

        # Build lookup of which (match, description) combos have trades placed
        trade_lookup = set()
        for tr in conn.execute("SELECT match, side FROM trades").fetchall():
            trade_lookup.add((tr["match"], tr["side"]))

        query = "SELECT * FROM signal_history WHERE 1=1"
        params: list = []
        if competition:
            query += " AND competition = ?"
            params.append(competition)
        if bet_type:
            query += " AND bet_type = ?"
            params.append(bet_type)
        if outcome:
            query += " AND outcome = ?"
            params.append(outcome)
        
        # Count total
        count_q = query.replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_q, params).fetchone()[0]
        
        query += " ORDER BY generated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(query, params).fetchall()
        
        signals = []
        for r in rows:
            signals.append({
                "id": r["id"],
                "generated_at": r["generated_at"],
                "event_ticker": r["event_ticker"],
                "market_ticker": r["market_ticker"],
                "match_title": r["match_title"],
                "competition": r["competition"],
                "bet_type": r["bet_type"],
                "description": r["description"],
                "model_prob": r["model_prob"],
                "kalshi_implied_prob": r["kalshi_implied_prob"],
                "edge": r["edge"],
                "confidence": r["confidence"],
                "reasoning": r["reasoning"],
                "kalshi_url": r["kalshi_url"],
                "entry_cents": r["entry_cents"],
                "upside_cents": r["upside_cents"],
                "score": r["score"],
                "home_crest": r["home_crest"] or "",
                "away_crest": r["away_crest"] or "",
                "league_emblem": r["league_emblem"] or "",
                "outcome": r["outcome"],
                "actual_pnl": r["actual_pnl"],
                "bet_placed": (r["match_title"], r["description"]) in trade_lookup,
            })
        return {"signals": signals, "total": total}
    finally:
        conn.close()


@app.get("/api/model-insights", response_model=ModelInsightsResponse)
def model_insights() -> ModelInsightsResponse:
    """Return per-match model insights: lambdas, strengths, scoreline matrix, distribution.

    Runs the full pipeline fresh each call (no separate cache — pipeline is
    already cached in `_signal_cache` if called recently).  Falls back to an
    empty list if the pipeline fails so the frontend degrades gracefully.
    """
    try:
        from football_intel.models.historical_data import load_historical_results
        from football_intel.models.calibrated_poisson import (
            CalibratedPoissonModel,
            _compute_scoreline_matrix,
            normalise_team_name,
            TeamStrength as _TS,
        )
        from football_intel.ingestion.kalshi_soccer import KalshiSoccerClient
        from football_intel.strategy.signal_generator import SignalGenerator

        # --- 1. Calibrate model ------------------------------------------
        results = load_historical_results()
        model = CalibratedPoissonModel()
        model.calibrate(results)

        # --- 2. Fetch Kalshi matches --------------------------------------
        ks_client = KalshiSoccerClient()
        matches = ks_client.fetch_match_markets()

        # --- 3. Generate signals -----------------------------------------
        generator = SignalGenerator(model)
        signals = generator.generate_signals(matches, min_edge=0.05)

        # Group signals by match_title for easy lookup
        signals_by_match: Dict[str, List[Any]] = {}
        for sig in signals:
            signals_by_match.setdefault(sig.match_title, []).append(sig)

        # Shared helpers
        crests = _load_crests()
        league_emblems = {
            "EPL": "https://crests.football-data.org/PL.png",
            "Bundesliga": "https://crests.football-data.org/BL1.png",
            "UCL": "https://crests.football-data.org/CL.png",
        }
        _default_strength = _TS(
            attack_home=1.0, attack_away=1.0,
            defense_home=1.0, defense_away=1.0,
            matches_played=0,
        )

        match_insights: List[MatchInsightResponse] = []
        for match in matches:
            match_title = f"{match.home_team} vs {match.away_team}"
            try:
                pred = model.predict_from_kalshi_match(match)
                comp = match.competition
                league = model.league_stats.get(comp)

                home_norm = normalise_team_name(match.home_team)
                away_norm = normalise_team_name(match.away_team)
                home_str = league.team_strengths.get(home_norm, _default_strength) if league else _default_strength
                away_str = league.team_strengths.get(away_norm, _default_strength) if league else _default_strength

                # Scoreline matrix → top 20 entries
                matrix = _compute_scoreline_matrix(pred.lambda_home, pred.lambda_away)
                sorted_lines = sorted(matrix.items(), key=lambda x: x[1], reverse=True)[:20]
                scoreline_matrix = [
                    ScorelineEntry(home_goals=h, away_goals=a, probability=round(p, 5))
                    for (h, a), p in sorted_lines
                ]

                # Goal distribution (0 through 7+)
                goal_dist: Dict[int, float] = {}
                for (h, a), p in matrix.items():
                    bucket = min(h + a, 7)
                    goal_dist[bucket] = goal_dist.get(bucket, 0.0) + p
                goal_distribution = [
                    GoalDistributionEntry(total_goals=g, probability=round(goal_dist.get(g, 0.0), 5))
                    for g in range(8)
                ]

                # Crests
                parts = match_title.split(" vs ")
                home_name = parts[0].strip() if len(parts) >= 2 else match_title
                away_name = parts[1].strip() if len(parts) >= 2 else ""
                home_crest = _find_crest(crests, home_name)
                away_crest = _find_crest(crests, away_name)
                league_emblem = league_emblems.get(comp, "")

                # Extract ALL Kalshi market prices for this match
                market_prices: Dict[str, float] = {}
                # Use both normalised and raw names for matching
                _home_lower = pred.home_team.lower()
                _away_lower = pred.away_team.lower()
                _raw_home_lower = match.home_team.lower()
                _raw_away_lower = match.away_team.lower()

                def _is_home(side_val: str, sub_val: str) -> bool:
                    s = side_val.upper()
                    return (s == "HOME" or s == match.home_team
                            or _home_lower in sub_val or _raw_home_lower in sub_val)

                def _is_away(side_val: str, sub_val: str) -> bool:
                    s = side_val.upper()
                    return (s == "AWAY" or s == match.away_team
                            or _away_lower in sub_val or _raw_away_lower in sub_val)

                for mkt in match.markets:
                    if mkt.implied_prob_yes is None or mkt.implied_prob_yes <= 0:
                        continue
                    p = round(mkt.implied_prob_yes, 4)
                    bt = mkt.bet_type
                    side = mkt.side or ""
                    sub = (mkt.yes_sub_title or "").lower()
                    if bt == "MONEYLINE":
                        if _is_home(side, sub):
                            market_prices["home_win"] = p
                        elif _is_away(side, sub):
                            market_prices["away_win"] = p
                        elif "draw" in sub or "tie" in sub or side.upper() == "DRAW":
                            market_prices["draw"] = p
                    elif bt == "OVER_UNDER" and mkt.line is not None:
                        is_under = "under" in sub
                        if is_under:
                            market_prices[f"under_{str(mkt.line).replace('.', '_')}"] = p
                        else:
                            market_prices[f"over_{str(mkt.line).replace('.', '_')}"] = p
                    elif bt == "BTTS":
                        if "no" in sub and "yes" not in sub:
                            market_prices["btts_no"] = p
                        else:
                            market_prices["btts_yes"] = p
                    elif bt == "FIRST_HALF":
                        if "draw" in sub or "tie" in sub:
                            market_prices["fh_draw"] = p
                        elif _is_home(side, sub):
                            market_prices["fh_home"] = p
                        elif _is_away(side, sub):
                            market_prices["fh_away"] = p
                    elif bt == "SPREAD" and mkt.line is not None:
                        line_key = str(mkt.line).replace('.', '_')
                        if _is_home(side, sub):
                            market_prices[f"spread_home_{line_key}"] = p
                        elif _is_away(side, sub):
                            market_prices[f"spread_away_{line_key}"] = p

                # Signals for this match → raw dicts
                match_signals = signals_by_match.get(match_title, [])
                sig_dicts: List[Dict[str, Any]] = []
                for i, sig in enumerate(match_signals, start=1):
                    entry_cents = int(round(sig.kalshi_implied_prob * 100))
                    sig_dicts.append({
                        "id": i,
                        "match_title": sig.match_title,
                        "competition": sig.competition,
                        "bet_type": sig.bet_type,
                        "description": sig.description,
                        "market_ticker": sig.market_ticker,
                        "model_prob": round(sig.model_prob, 4),
                        "kalshi_implied_prob": round(sig.kalshi_implied_prob, 4),
                        "edge": round(sig.edge, 4),
                        "confidence": sig.confidence,
                        "reasoning": sig.reasoning,
                        "kalshi_url": sig.kalshi_url,
                        "entry_cents": entry_cents,
                        "upside_cents": 100 - entry_cents,
                        "score": int(min(sig.edge * sig.model_prob * 400, 100)),
                    })

                match_insights.append(
                    MatchInsightResponse(
                        match_title=match_title,
                        competition=comp,
                        home_team=match.home_team,
                        away_team=match.away_team,
                        kickoff_utc=match.kickoff_utc.isoformat() if match.kickoff_utc else None,
                        home_crest=home_crest,
                        away_crest=away_crest,
                        league_emblem=league_emblem,
                        lambda_home=round(pred.lambda_home, 3),
                        lambda_away=round(pred.lambda_away, 3),
                        home_strength=TeamStrengthData(
                            attack_home=round(home_str.attack_home, 3),
                            attack_away=round(home_str.attack_away, 3),
                            defense_home=round(home_str.defense_home, 3),
                            defense_away=round(home_str.defense_away, 3),
                            matches_played=home_str.matches_played,
                        ),
                        away_strength=TeamStrengthData(
                            attack_home=round(away_str.attack_home, 3),
                            attack_away=round(away_str.attack_away, 3),
                            defense_home=round(away_str.defense_home, 3),
                            defense_away=round(away_str.defense_away, 3),
                            matches_played=away_str.matches_played,
                        ),
                        league_avg_home_goals=round(league.avg_home_goals, 3) if league else 1.5,
                        league_avg_away_goals=round(league.avg_away_goals, 3) if league else 1.2,
                        prob_1x2=Prob1X2(
                            home=round(pred.prob_home_win, 4),
                            draw=round(pred.prob_draw, 4),
                            away=round(pred.prob_away_win, 4),
                        ),
                        prob_over_under=ProbOverUnder(
                            over_1_5=round(pred.prob_over_1_5, 4),
                            over_2_5=round(pred.prob_over_2_5, 4),
                            over_3_5=round(pred.prob_over_3_5, 4),
                            over_4_5=round(pred.prob_over_4_5, 4),
                        ),
                        prob_btts=round(pred.prob_btts_yes, 4),
                        prob_first_half=FirstHalfProbs(
                            home=round(pred.prob_first_half_home, 4),
                            draw=round(pred.prob_first_half_draw, 4),
                            away=round(pred.prob_first_half_away, 4),
                        ),
                        scoreline_matrix=scoreline_matrix,
                        goal_distribution=goal_distribution,
                        market_prices=market_prices,
                        flagged_signals=sig_dicts,
                    )
                )
            except Exception as exc:
                import logging as _log
                _log.getLogger(__name__).warning(
                    "model_insights: skipping match '%s': %s", match_title, exc
                )

        return ModelInsightsResponse(matches=match_insights)

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Model insights pipeline error: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Adaptive Tuning endpoints
# ---------------------------------------------------------------------------


def _build_adaptive_params_response(params_dict: dict) -> AdaptiveParamsResponse:
    return AdaptiveParamsResponse(
        min_edge_by_type=params_dict["min_edge_by_type"],
        min_prob_by_type=params_dict["min_prob_by_type"],
        shrinkage_alpha_by_conf=params_dict["shrinkage_alpha_by_conf"],
        max_edge=params_dict["max_edge"],
        enabled_bet_types=params_dict["enabled_bet_types"],
        enabled_confidence=params_dict["enabled_confidence"],
        updated_at=params_dict["updated_at"],
        sample_size=params_dict["sample_size"],
        version=params_dict["version"],
    )


@app.get("/api/adaptive", response_model=AdaptiveReportResponse)
def adaptive_report() -> AdaptiveReportResponse:
    """Return current adaptive tuning params and performance analysis."""
    try:
        from football_intel.strategy.adaptive import AdaptiveAnalyzer
        analyzer = AdaptiveAnalyzer()
        report = analyzer.get_analysis_report()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Adaptive analysis error: {exc}",
        ) from exc

    def _gs(d: dict) -> GroupStats:
        return GroupStats(**d)

    return AdaptiveReportResponse(
        status=report["status"],
        total_settled=report["total_settled"],
        samples_needed=report["samples_needed"],
        min_samples=report["min_samples"],
        current_params=_build_adaptive_params_response(report["current_params"]),
        default_params=_build_adaptive_params_response(report["default_params"]),
        edge_deltas=report["edge_deltas"],
        alpha_deltas=report["alpha_deltas"],
        by_bet_type={k: _gs(v) for k, v in report["by_bet_type"].items()},
        by_edge_bucket={k: _gs(v) for k, v in report["by_edge_bucket"].items()},
        by_prob_bucket={k: _gs(v) for k, v in report["by_prob_bucket"].items()},
        by_confidence={k: _gs(v) for k, v in report["by_confidence"].items()},
        calibration=[
            CalibrationPoint(**c) for c in report["calibration"]
        ],
        last_updated=report["last_updated"],
        version=report["version"],
    )


@app.post("/api/adaptive/retune", response_model=RetuneResponse)
def adaptive_retune() -> RetuneResponse:
    """Trigger a fresh adaptive analysis and update parameters."""
    try:
        from football_intel.strategy.adaptive import AdaptiveAnalyzer
        analyzer = AdaptiveAnalyzer()
        analysis = analyzer.analyze_settled_trades()
        total_settled = analysis["total_settled"]

        if total_settled < AdaptiveAnalyzer.MIN_SAMPLES:
            return RetuneResponse(
                success=False,
                message=(
                    f"Not enough data: {total_settled}/{AdaptiveAnalyzer.MIN_SAMPLES} "
                    f"settled trades needed."
                ),
                new_params=None,
                total_settled=total_settled,
                version=analyzer.load_params().version,
            )

        new_params = analyzer.compute_optimal_params(analysis)
        analyzer.save_params(new_params)

        # Reload signal cache so next signal request uses new params
        _signal_cache.clear()

        return RetuneResponse(
            success=True,
            message=f"Parameters updated to v{new_params.version} ({total_settled} samples).",
            new_params=_build_adaptive_params_response(new_params.to_dict()),
            total_settled=total_settled,
            version=new_params.version,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Retune error: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# Static file serving for the Vite-built frontend (Docker / production)
# This must come AFTER all API routes so it doesn't swallow /api/* paths.
# ---------------------------------------------------------------------------

import os as _os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_STATIC_DIR = _os.path.join(_os.path.dirname(__file__), '..', 'web', 'dist')
if _os.path.isdir(_STATIC_DIR):
    # Serve static assets (JS, CSS, images)
    app.mount(
        '/assets',
        StaticFiles(directory=_os.path.join(_STATIC_DIR, 'assets')),
        name='static-assets',
    )

    # Catch-all for SPA routing — must be the very last route
    @app.get('/{path:path}')
    async def serve_spa(path: str) -> FileResponse:
        file_path = _os.path.join(_STATIC_DIR, path)
        if _os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(_os.path.join(_STATIC_DIR, 'index.html'))


# ---------------------------------------------------------------------------
# Runner (direct invocation)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "football_intel.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
