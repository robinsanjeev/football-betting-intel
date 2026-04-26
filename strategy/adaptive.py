"""Adaptive feedback loop for the Football Intel signal generator.

Analyzes settled trade outcomes from signal_history and automatically
tunes signal-generation parameters over time.

Usage:
    from football_intel.strategy.adaptive import AdaptiveAnalyzer, AdaptiveParams

    analyzer = AdaptiveAnalyzer()
    analysis = analyzer.analyze_settled_trades()
    if analysis["total_settled"] >= AdaptiveAnalyzer.MIN_SAMPLES:
        params = analyzer.compute_optimal_params(analysis)
        analyzer.save_params(params)
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# DB path helper (mirrors the one in api/main.py)
# ---------------------------------------------------------------------------

def _get_db_path() -> str:
    return os.environ.get(
        "FOOTBALL_INTEL_DB",
        "football_intel/data/football_intel.db",
    )


def _get_conn() -> sqlite3.Connection:
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Default values (mirrors current signal_generator.py hardcoded values)
# ---------------------------------------------------------------------------

_DEFAULT_MIN_EDGE_BY_TYPE: Dict[str, float] = {
    "MONEYLINE": 0.15,
    "OVER_UNDER": 0.05,
    "BTTS": 0.08,
    "SPREAD": 0.10,
    "FIRST_HALF": 0.10,
}

_DEFAULT_MIN_PROB_BY_TYPE: Dict[str, float] = {
    "MONEYLINE": 0.45,
    "OVER_UNDER": 0.50,
    "BTTS": 0.45,
    "SPREAD": 0.45,
    "FIRST_HALF": 0.45,
}

_DEFAULT_MIN_COMPOSITE_SCORE: float = 50.0

_DEFAULT_SHRINKAGE_ALPHA_BY_CONF: Dict[str, float] = {
    "HIGH": 0.7,
    "MEDIUM": 0.5,
    "LOW": 0.3,
}

_DEFAULT_MAX_EDGE: float = 0.25
_DEFAULT_ENABLED_BET_TYPES: List[str] = [
    "MONEYLINE", "OVER_UNDER", "BTTS", "SPREAD", "FIRST_HALF"
]
_DEFAULT_ENABLED_CONFIDENCE: List[str] = ["HIGH", "MEDIUM", "LOW"]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class AdaptiveParams:
    """Tunable parameters that the feedback loop can adjust."""

    min_edge_by_type: Dict[str, float]        # bet_type → min edge threshold
    min_prob_by_type: Dict[str, float]         # bet_type → min model probability
    shrinkage_alpha_by_conf: Dict[str, float]  # confidence → shrinkage alpha
    max_edge: float                             # global edge cap
    enabled_bet_types: List[str]               # which bet types to include
    enabled_confidence: List[str]              # which confidence levels to include
    updated_at: str                             # ISO timestamp
    sample_size: int                            # how many settled trades this was based on
    version: int                                # increment each update
    min_composite_score: float = _DEFAULT_MIN_COMPOSITE_SCORE  # minimum composite score to emit signal

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AdaptiveParams":
        return cls(
            min_edge_by_type=d.get("min_edge_by_type", dict(_DEFAULT_MIN_EDGE_BY_TYPE)),
            min_prob_by_type=d.get("min_prob_by_type", dict(_DEFAULT_MIN_PROB_BY_TYPE)),
            shrinkage_alpha_by_conf=d.get(
                "shrinkage_alpha_by_conf", dict(_DEFAULT_SHRINKAGE_ALPHA_BY_CONF)
            ),
            max_edge=d.get("max_edge", _DEFAULT_MAX_EDGE),
            enabled_bet_types=d.get("enabled_bet_types", list(_DEFAULT_ENABLED_BET_TYPES)),
            enabled_confidence=d.get("enabled_confidence", list(_DEFAULT_ENABLED_CONFIDENCE)),
            updated_at=d.get("updated_at", datetime.now(tz=timezone.utc).isoformat()),
            sample_size=d.get("sample_size", 0),
            version=d.get("version", 0),
            min_composite_score=d.get("min_composite_score", _DEFAULT_MIN_COMPOSITE_SCORE),
        )

    @classmethod
    def defaults(cls) -> "AdaptiveParams":
        return cls(
            min_edge_by_type=dict(_DEFAULT_MIN_EDGE_BY_TYPE),
            min_prob_by_type=dict(_DEFAULT_MIN_PROB_BY_TYPE),
            shrinkage_alpha_by_conf=dict(_DEFAULT_SHRINKAGE_ALPHA_BY_CONF),
            max_edge=_DEFAULT_MAX_EDGE,
            enabled_bet_types=list(_DEFAULT_ENABLED_BET_TYPES),
            enabled_confidence=list(_DEFAULT_ENABLED_CONFIDENCE),
            updated_at=datetime.now(tz=timezone.utc).isoformat(),
            sample_size=0,
            version=0,
            min_composite_score=_DEFAULT_MIN_COMPOSITE_SCORE,
        )


# ---------------------------------------------------------------------------
# Adaptive analysis helpers
# ---------------------------------------------------------------------------

def _edge_bucket(edge: float) -> str:
    """Return the edge bucket label for a given edge value."""
    if edge < 0.12:
        return "8-12%"
    if edge < 0.16:
        return "12-16%"
    if edge < 0.20:
        return "16-20%"
    return "20%+"


def _prob_bucket(prob: float) -> str:
    """Return the probability bucket label for a given model probability."""
    if prob < 0.30:
        return "15-30%"
    if prob < 0.45:
        return "30-45%"
    if prob < 0.60:
        return "45-60%"
    if prob < 0.75:
        return "60-75%"
    return "75%+"


def _predicted_midpoint(bucket: str) -> float:
    """Return the expected predicted win rate (midpoint) for a prob bucket."""
    mapping = {
        "15-30%": 0.225,
        "30-45%": 0.375,
        "45-60%": 0.525,
        "60-75%": 0.675,
        "75%+": 0.825,
    }
    return mapping.get(bucket, 0.5)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Main analyzer class
# ---------------------------------------------------------------------------

class AdaptiveAnalyzer:
    """Analyzes settled trades to compute optimal signal parameters."""

    PARAMS_PATH = "football_intel/data/adaptive_params.json"
    MIN_SAMPLES = 20  # minimum settled trades before adapting

    # Parameter bounds
    EDGE_LO: float = 0.05
    EDGE_HI: float = 0.20
    PROB_LO: float = 0.10
    PROB_HI: float = 0.40
    ALPHA_LO: float = 0.2
    ALPHA_HI: float = 0.8

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load_params(self) -> AdaptiveParams:
        """Load adaptive parameters from JSON file, or return defaults."""
        try:
            path = self.PARAMS_PATH
            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
                params = AdaptiveParams.from_dict(data)
                logger.debug(
                    "Loaded adaptive params v%d (sample_size=%d)",
                    params.version, params.sample_size,
                )
                return params
        except Exception as exc:
            logger.warning("Could not load adaptive params: %s — using defaults", exc)
        return AdaptiveParams.defaults()

    def save_params(self, params: AdaptiveParams) -> None:
        """Persist adaptive parameters to JSON file."""
        path = self.PARAMS_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(params.to_dict(), f, indent=2)
        logger.info(
            "Saved adaptive params v%d (sample_size=%d) → %s",
            params.version, params.sample_size, path,
        )

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def analyze_settled_trades(self) -> Dict[str, Any]:
        """Read settled trades and compute performance breakdowns.

        Returns a dict with:
            total_settled: int
            by_bet_type: Dict[str, GroupStats]
            by_edge_bucket: Dict[str, GroupStats]
            by_prob_bucket: Dict[str, GroupStats]
            by_confidence: Dict[str, GroupStats]
        Where GroupStats = {count, wins, win_rate, total_pnl, total_staked, roi, avg_edge, calibration_error}
        """
        conn = _get_conn()
        try:
            # Ensure table exists (graceful degradation when DB is fresh)
            conn.execute(
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
                )
                """
            )
            rows = conn.execute(
                """
                SELECT bet_type, model_prob, kalshi_implied_prob, edge, confidence,
                       outcome, actual_pnl, entry_cents
                FROM signal_history
                WHERE outcome IN ('WIN', 'LOSE')
                """
            ).fetchall()
        finally:
            conn.close()

        total = len(rows)

        # Accumulators: each value is a dict with count, wins, total_pnl, total_staked, edges
        def empty_group() -> Dict[str, Any]:
            return {
                "count": 0,
                "wins": 0,
                "total_pnl": 0.0,
                "total_staked": 10.0 * 0,  # will accumulate below
                "edges": [],
                "model_probs": [],
            }

        by_bet_type: Dict[str, Any] = {}
        by_edge_bucket: Dict[str, Any] = {}
        by_prob_bucket: Dict[str, Any] = {}
        by_confidence: Dict[str, Any] = {}

        stake = 10.0  # standard paper trade stake

        for row in rows:
            bt = row["bet_type"] or "UNKNOWN"
            edge = float(row["edge"] or 0.0)
            model_prob = float(row["model_prob"] or 0.0)
            confidence = row["confidence"] or "LOW"
            outcome = row["outcome"]
            pnl = float(row["actual_pnl"] or 0.0)
            is_win = outcome == "WIN"

            eb = _edge_bucket(edge)
            pb = _prob_bucket(model_prob)

            for key, d_map in [
                (bt, by_bet_type),
                (eb, by_edge_bucket),
                (pb, by_prob_bucket),
                (confidence, by_confidence),
            ]:
                if key not in d_map:
                    d_map[key] = empty_group()
                g = d_map[key]
                g["count"] += 1
                g["wins"] += 1 if is_win else 0
                g["total_pnl"] += pnl
                g["total_staked"] = g["total_staked"] + stake if g["count"] > 1 else stake
                g["edges"].append(edge)
                g["model_probs"].append(model_prob)

        def _finalize(d_map: Dict[str, Any]) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            for key, g in d_map.items():
                count = g["count"]
                wins = g["wins"]
                total_pnl = g["total_pnl"]
                total_staked = count * stake  # simpler to recompute
                win_rate = wins / count if count > 0 else 0.0
                roi = total_pnl / total_staked if total_staked > 0 else 0.0
                avg_edge = sum(g["edges"]) / count if count > 0 else 0.0
                avg_model_prob = (
                    sum(g["model_probs"]) / count if count > 0 else 0.0
                )
                # Calibration error: predicted win rate (avg model prob) vs actual win rate
                calib_error = avg_model_prob - win_rate
                result[key] = {
                    "count": count,
                    "wins": wins,
                    "win_rate": round(win_rate, 4),
                    "total_pnl": round(total_pnl, 2),
                    "total_staked": round(total_staked, 2),
                    "roi": round(roi, 4),
                    "avg_edge": round(avg_edge, 4),
                    "avg_model_prob": round(avg_model_prob, 4),
                    "calibration_error": round(calib_error, 4),
                }
            return result

        return {
            "total_settled": total,
            "by_bet_type": _finalize(by_bet_type),
            "by_edge_bucket": _finalize(by_edge_bucket),
            "by_prob_bucket": _finalize(by_prob_bucket),
            "by_confidence": _finalize(by_confidence),
        }

    # ------------------------------------------------------------------
    # Parameter optimization
    # ------------------------------------------------------------------

    def compute_optimal_params(
        self, analysis: Dict[str, Any]
    ) -> AdaptiveParams:
        """Compute new parameter recommendations based on trade analysis.

        Tuning logic:
        - Negative ROI bet_type over 20+ samples → raise min_edge by 2%
        - Positive ROI bet_type → lower min_edge by 1% (floor 5%)
        - Prob bucket consistently underperforms → raise min_prob for that type
        - LOW confidence < 30% win rate over 15+ samples → disable LOW
        - Shrinkage adjustments based on calibration error
        """
        # Start from current saved params (or defaults)
        current = self.load_params()

        new_min_edge = dict(current.min_edge_by_type)
        new_min_prob = dict(current.min_prob_by_type)
        new_alpha = dict(current.shrinkage_alpha_by_conf)
        new_max_edge = current.max_edge
        new_enabled_types = list(current.enabled_bet_types)
        new_enabled_conf = list(current.enabled_confidence)

        total_settled = analysis.get("total_settled", 0)
        by_bet_type = analysis.get("by_bet_type", {})
        by_prob_bucket = analysis.get("by_prob_bucket", {})
        by_confidence = analysis.get("by_confidence", {})

        # --- 1. Tune min_edge_by_type based on ROI per bet type ----------
        for bet_type in _DEFAULT_ENABLED_BET_TYPES:
            stats = by_bet_type.get(bet_type)
            if stats is None or stats["count"] < 20:
                continue
            roi = stats["roi"]
            current_edge = new_min_edge.get(bet_type, 0.08)
            if roi < 0:
                # Negative ROI → be more selective (raise min_edge by 2%)
                new_edge = _clamp(current_edge + 0.02, self.EDGE_LO, self.EDGE_HI)
                logger.info(
                    "Adaptive: %s negative ROI (%.1f%%) → raising min_edge %.2f → %.2f",
                    bet_type, roi * 100, current_edge, new_edge,
                )
            else:
                # Positive ROI → slightly lower barrier (lower min_edge by 1%)
                new_edge = _clamp(current_edge - 0.01, self.EDGE_LO, self.EDGE_HI)
                logger.info(
                    "Adaptive: %s positive ROI (%.1f%%) → lowering min_edge %.2f → %.2f",
                    bet_type, roi * 100, current_edge, new_edge,
                )
            new_min_edge[bet_type] = round(new_edge, 4)

        # --- 2. Tune min_prob based on probability bucket calibration -----
        # If a prob bucket's actual win rate is >10pp below predicted → raise min_prob
        for bucket, stats in by_prob_bucket.items():
            if stats["count"] < 10:
                continue
            predicted_mid = _predicted_midpoint(bucket)
            actual_wr = stats["win_rate"]
            calib_error = predicted_mid - actual_wr
            if calib_error > 0.10:
                # Model is overconfident in this probability range → raise min_prob
                for bet_type in _DEFAULT_ENABLED_BET_TYPES:
                    cur_prob = new_min_prob.get(bet_type, 0.15)
                    new_prob = _clamp(cur_prob + 0.02, self.PROB_LO, self.PROB_HI)
                    logger.info(
                        "Adaptive: prob_bucket %s underperforms (calib_error=%.2f) → "
                        "raising min_prob for %s: %.2f → %.2f",
                        bucket, calib_error, bet_type, cur_prob, new_prob,
                    )
                    new_min_prob[bet_type] = round(new_prob, 4)
                break  # apply once per update cycle

        # --- 3. Confidence level tuning ----------------------------------
        low_stats = by_confidence.get("LOW")
        if low_stats and low_stats["count"] >= 15:
            if low_stats["win_rate"] < 0.30:
                if "LOW" in new_enabled_conf:
                    new_enabled_conf.remove("LOW")
                    logger.info(
                        "Adaptive: LOW confidence win_rate=%.1f%% < 30%% → disabling LOW confidence",
                        low_stats["win_rate"] * 100,
                    )
            else:
                # Re-enable if win rate has recovered (> 35%)
                if "LOW" not in new_enabled_conf and low_stats["win_rate"] >= 0.35:
                    new_enabled_conf.append("LOW")
                    logger.info(
                        "Adaptive: LOW confidence win_rate=%.1f%% recovered → re-enabling",
                        low_stats["win_rate"] * 100,
                    )

        # --- 4. Shrinkage alpha tuning based on calibration error --------
        for conf in ["HIGH", "MEDIUM", "LOW"]:
            stats = by_confidence.get(conf)
            if stats is None or stats["count"] < 10:
                continue
            # calibration_error > 0 means model is overconfident (should shrink more)
            # calibration_error < 0 means model underestimates (can shrink less)
            calib = stats["calibration_error"]
            cur_alpha = new_alpha.get(conf, _DEFAULT_SHRINKAGE_ALPHA_BY_CONF.get(conf, 0.5))
            if calib > 0.08:
                # Model too confident → reduce alpha (shrink more toward market)
                new_a = _clamp(cur_alpha - 0.05, self.ALPHA_LO, self.ALPHA_HI)
                logger.info(
                    "Adaptive: %s calibration error=%.2f (overconfident) → "
                    "reducing alpha %.2f → %.2f",
                    conf, calib, cur_alpha, new_a,
                )
                new_alpha[conf] = round(new_a, 3)
            elif calib < -0.08:
                # Model underestimates → increase alpha (trust model more)
                new_a = _clamp(cur_alpha + 0.05, self.ALPHA_LO, self.ALPHA_HI)
                logger.info(
                    "Adaptive: %s calibration error=%.2f (underconfident) → "
                    "increasing alpha %.2f → %.2f",
                    conf, calib, cur_alpha, new_a,
                )
                new_alpha[conf] = round(new_a, 3)

        # --- 5. Build updated params -------------------------------------
        new_params = AdaptiveParams(
            min_edge_by_type=new_min_edge,
            min_prob_by_type=new_min_prob,
            shrinkage_alpha_by_conf=new_alpha,
            max_edge=new_max_edge,
            enabled_bet_types=new_enabled_types,
            enabled_confidence=new_enabled_conf,
            updated_at=datetime.now(tz=timezone.utc).isoformat(),
            sample_size=total_settled,
            version=current.version + 1,
        )
        return new_params

    # ------------------------------------------------------------------
    # Analysis report (for the API endpoint)
    # ------------------------------------------------------------------

    def get_analysis_report(self) -> Dict[str, Any]:
        """Return a comprehensive analysis report dict for the API.

        Includes:
          - Warming-up state info
          - Performance by bet_type, edge_bucket, prob_bucket, confidence
          - Current params vs defaults
          - Calibration data
        """
        analysis = self.analyze_settled_trades()
        current_params = self.load_params()
        defaults = AdaptiveParams.defaults()

        total_settled = analysis["total_settled"]
        is_warming_up = total_settled < self.MIN_SAMPLES

        # Calibration data: predicted midpoint vs actual win rate per prob bucket
        calibration_buckets = []
        for bucket in ["15-30%", "30-45%", "45-60%", "60-75%", "75%+"]:
            stats = analysis["by_prob_bucket"].get(bucket, {})
            calibration_buckets.append({
                "bucket": bucket,
                "predicted_midpoint": _predicted_midpoint(bucket),
                "actual_win_rate": stats.get("win_rate"),
                "count": stats.get("count", 0),
                "calibration_error": stats.get("calibration_error"),
            })

        # Delta between current params and defaults
        def _edge_deltas() -> Dict[str, float]:
            d: Dict[str, float] = {}
            for bt in _DEFAULT_ENABLED_BET_TYPES:
                cur = current_params.min_edge_by_type.get(bt, 0.08)
                def_v = defaults.min_edge_by_type.get(bt, 0.08)
                d[bt] = round(cur - def_v, 4)
            return d

        def _alpha_deltas() -> Dict[str, float]:
            d: Dict[str, float] = {}
            for conf in ["HIGH", "MEDIUM", "LOW"]:
                cur = current_params.shrinkage_alpha_by_conf.get(conf, 0.5)
                def_v = defaults.shrinkage_alpha_by_conf.get(conf, 0.5)
                d[conf] = round(cur - def_v, 4)
            return d

        return {
            "status": "WARMING_UP" if is_warming_up else "ACTIVE",
            "total_settled": total_settled,
            "samples_needed": max(0, self.MIN_SAMPLES - total_settled),
            "min_samples": self.MIN_SAMPLES,
            "current_params": current_params.to_dict(),
            "default_params": defaults.to_dict(),
            "edge_deltas": _edge_deltas(),
            "alpha_deltas": _alpha_deltas(),
            "by_bet_type": analysis["by_bet_type"],
            "by_edge_bucket": analysis["by_edge_bucket"],
            "by_prob_bucket": analysis["by_prob_bucket"],
            "by_confidence": analysis["by_confidence"],
            "calibration": calibration_buckets,
            "last_updated": current_params.updated_at,
            "version": current_params.version,
        }
