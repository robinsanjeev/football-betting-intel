"""Pydantic response models for the Football Intel API."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class Signal(BaseModel):
    event_ticker: str
    match_title: str
    competition: str
    bet_type: str
    description: str
    market_ticker: str
    model_prob: float
    kalshi_implied_prob: float
    edge: float
    ev_per_dollar: float
    confidence: str
    reasoning: str
    kalshi_url: str
    entry_cents: int        # Kalshi entry price in cents (= round(implied_prob * 100))
    upside_cents: int       # Profit if correct in cents (= 100 - entry_cents)
    score: int              # 0-100 edge score: int(min(edge * 200, 100))
    home_crest: str = ""    # URL to home team crest image
    away_crest: str = ""    # URL to away team crest image
    league_emblem: str = "" # URL to league/competition emblem
    composite_score: float = 0.0     # 0-100 composite score (confidence-centric)
    score_breakdown: str = ""        # human-readable breakdown


class SignalResponse(Signal):
    id: int


class SignalHistoryEntry(BaseModel):
    id: int
    generated_at: str
    event_ticker: str
    market_ticker: str
    match_title: str
    competition: str
    bet_type: str
    description: str
    model_prob: float
    kalshi_implied_prob: float
    edge: float
    confidence: str
    reasoning: str
    kalshi_url: str
    entry_cents: int
    upside_cents: int
    score: int
    home_crest: Optional[str] = None
    away_crest: Optional[str] = None
    league_emblem: Optional[str] = None
    outcome: str = "PENDING"
    actual_pnl: float = 0.0


class SignalsListResponse(BaseModel):
    signals: List[SignalResponse]
    generated_at: str           # ISO-8601 UTC string
    total_matches_scanned: int


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

class TradeResponse(BaseModel):
    id: int
    timestamp: str
    match: str
    side: str
    stake: float
    odds: float
    implied_prob: float         # 1 / odds
    result: str                 # PENDING / WIN / LOSE
    pnl: float


class TradesListResponse(BaseModel):
    trades: List[TradeResponse]
    total: int
    pending: int
    settled: int


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

class CumulativePnLPoint(BaseModel):
    date: str
    pnl: float


class WeeklyROIPoint(BaseModel):
    week: str           # e.g. "2026-W16"
    roi: float
    trades: int


class PerformanceResponse(BaseModel):
    total_trades: int
    settled_trades: int
    pending_trades: int
    win_rate: float
    roi: float
    total_pnl: float
    max_drawdown: float
    total_staked: float
    cumulative_pnl: List[CumulativePnLPoint]
    weekly_roi: List[WeeklyROIPoint]
    win_loss_counts: Dict[str, int]
    avg_composite_score_winners: Optional[float] = None
    avg_composite_score_losers: Optional[float] = None


# ---------------------------------------------------------------------------
# Accuracy / calibration
# ---------------------------------------------------------------------------

class CalibrationBucket(BaseModel):
    bucket: str                         # e.g. "0-10%"
    predicted_prob: float               # midpoint of bucket
    actual_win_rate: Optional[float]    # None if no trades in bucket
    count: int


class RollingWinRatePoint(BaseModel):
    trade_number: int
    rolling_10_win_rate: Optional[float]    # None until 10 settled trades


class AccuracyResponse(BaseModel):
    calibration: List[CalibrationBucket]
    rolling_win_rate: List[RollingWinRatePoint]
    total_settled: int
    message: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    db_path: str
    db_accessible: bool
    cache_stale: bool
    signals_cached: int


# ---------------------------------------------------------------------------
# Model Insights
# ---------------------------------------------------------------------------

class TeamStrengthData(BaseModel):
    attack_home: float
    attack_away: float
    defense_home: float
    defense_away: float
    matches_played: int


class ScorelineEntry(BaseModel):
    home_goals: int
    away_goals: int
    probability: float


class GoalDistributionEntry(BaseModel):
    total_goals: int   # 0-6 are exact; 7 represents "7+"
    probability: float


class Prob1X2(BaseModel):
    home: float
    draw: float
    away: float


class ProbOverUnder(BaseModel):
    over_1_5: float
    over_2_5: float
    over_3_5: float
    over_4_5: float


class FirstHalfProbs(BaseModel):
    home: float
    draw: float
    away: float


class MatchInsightResponse(BaseModel):
    match_title: str
    competition: str
    home_team: str
    away_team: str
    kickoff_utc: Optional[str] = None  # ISO-8601 kickoff time
    home_crest: str
    away_crest: str
    league_emblem: str
    lambda_home: float
    lambda_away: float
    home_strength: TeamStrengthData
    away_strength: TeamStrengthData
    league_avg_home_goals: float
    league_avg_away_goals: float
    prob_1x2: Prob1X2
    prob_over_under: ProbOverUnder
    prob_btts: float
    prob_first_half: FirstHalfProbs
    scoreline_matrix: List[ScorelineEntry]
    goal_distribution: List[GoalDistributionEntry]
    market_prices: Dict[str, float]   # label → Kalshi implied prob (e.g. "home_win": 0.55)
    flagged_signals: List[Dict]   # reuses the raw signal dict format


class ModelInsightsResponse(BaseModel):
    matches: List[MatchInsightResponse]


# ---------------------------------------------------------------------------
# Adaptive Tuning
# ---------------------------------------------------------------------------

class GroupStats(BaseModel):
    """Performance stats for a given grouping (bet_type, edge range, etc.)."""
    count: int
    wins: int
    win_rate: float
    total_pnl: float
    total_staked: float
    roi: float
    avg_edge: float
    avg_model_prob: float
    calibration_error: float


class CalibrationPoint(BaseModel):
    """Predicted vs actual win rate for a probability bucket."""
    bucket: str               # e.g. "30-45%"
    predicted_midpoint: float
    actual_win_rate: Optional[float]
    count: int
    calibration_error: Optional[float]


class AdaptiveParamsResponse(BaseModel):
    """Current adaptive parameters (mirrors AdaptiveParams dataclass)."""
    min_edge_by_type: Dict[str, float]
    min_prob_by_type: Dict[str, float]
    shrinkage_alpha_by_conf: Dict[str, float]
    max_edge: float
    enabled_bet_types: List[str]
    enabled_confidence: List[str]
    updated_at: str
    sample_size: int
    version: int
    min_composite_score: float = 50.0


class AdaptiveReportResponse(BaseModel):
    """Full adaptive tuning report returned by GET /api/adaptive."""
    status: str                           # "ACTIVE" or "WARMING_UP"
    total_settled: int
    samples_needed: int
    min_samples: int
    current_params: AdaptiveParamsResponse
    default_params: AdaptiveParamsResponse
    edge_deltas: Dict[str, float]         # bet_type → delta from default
    alpha_deltas: Dict[str, float]        # confidence → delta from default
    by_bet_type: Dict[str, GroupStats]
    by_edge_bucket: Dict[str, GroupStats]
    by_prob_bucket: Dict[str, GroupStats]
    by_confidence: Dict[str, GroupStats]
    calibration: List[CalibrationPoint]
    last_updated: str
    version: int


class RetuneResponse(BaseModel):
    """Response from POST /api/adaptive/retune."""
    success: bool
    message: str
    new_params: Optional[AdaptiveParamsResponse] = None
    total_settled: int
    version: int


# ---------------------------------------------------------------------------
# Odds Snapshots / Movement
# ---------------------------------------------------------------------------

class OddsSnapshotResponse(BaseModel):
    """A single odds snapshot for a market."""
    id: Optional[int] = None
    market_ticker: str
    snapshot_time: str
    kalshi_implied_prob: float
    model_prob: float
    edge: float


class OddsMovementResponse(BaseModel):
    """Odds movement history for a specific market."""
    market_ticker: str
    snapshots: List[OddsSnapshotResponse]
    total_snapshots: int
    positive_snapshots: int
    is_persistent: bool
    is_new: bool


class AllOddsMovementResponse(BaseModel):
    """Odds movement for all tracked markets."""
    markets: Dict[str, OddsMovementResponse]


class SnapshotTriggerResponse(BaseModel):
    """Response from POST /api/odds/snapshot."""
    success: bool
    message: str
    snapshots_recorded: int
