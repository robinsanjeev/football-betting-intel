"""Basic tests for the calibrated Poisson model."""
import pytest
from football_intel.models.calibrated_poisson import CalibratedPoissonModel, _compute_scoreline_matrix
from football_intel.models.historical_data import MatchResult
from datetime import datetime


def test_scoreline_matrix_sums_to_one():
    """Scoreline probability matrix should sum to ~1.0."""
    matrix = _compute_scoreline_matrix(1.5, 1.2)
    total = sum(matrix.values())
    assert abs(total - 1.0) < 0.01, f"Matrix sums to {total}, expected ~1.0"


def test_scoreline_matrix_non_negative():
    """All probabilities should be non-negative."""
    matrix = _compute_scoreline_matrix(1.5, 1.2)
    for (h, a), p in matrix.items():
        assert p >= 0, f"Negative probability at ({h},{a}): {p}"


def test_calibration_produces_strengths():
    """Model should produce team strengths after calibration."""
    results = [
        MatchResult("Team A", "Team B", 2, 1, "PL", datetime(2026, 1, 1)),
        MatchResult("Team B", "Team A", 0, 3, "PL", datetime(2026, 1, 8)),
        MatchResult("Team A", "Team C", 1, 1, "PL", datetime(2026, 1, 15)),
        MatchResult("Team C", "Team A", 2, 2, "PL", datetime(2026, 1, 22)),
        MatchResult("Team B", "Team C", 1, 0, "PL", datetime(2026, 2, 1)),
        MatchResult("Team C", "Team B", 0, 1, "PL", datetime(2026, 2, 8)),
    ]
    model = CalibratedPoissonModel()
    model.calibrate(results)
    assert "EPL" in model.league_stats
    assert len(model.league_stats["EPL"].team_strengths) >= 3


def test_prediction_returns_valid_probs():
    """Predictions should have probabilities that sum to ~1.0."""
    results = [
        MatchResult("Team A", "Team B", 2, 1, "PL", datetime(2026, 1, 1)),
        MatchResult("Team B", "Team A", 0, 3, "PL", datetime(2026, 1, 8)),
        MatchResult("Team A", "Team C", 1, 1, "PL", datetime(2026, 1, 15)),
        MatchResult("Team C", "Team B", 2, 0, "PL", datetime(2026, 1, 22)),
    ]
    model = CalibratedPoissonModel()
    model.calibrate(results)
    pred = model.predict_match("Team A", "Team B", "EPL")
    total_1x2 = pred.prob_home_win + pred.prob_draw + pred.prob_away_win
    assert abs(total_1x2 - 1.0) < 0.02, f"1X2 probs sum to {total_1x2}"
    assert 0 < pred.lambda_home < 10
    assert 0 < pred.lambda_away < 10


def test_prediction_unknown_team_uses_defaults():
    """Unknown teams should get league-average predictions, not crash."""
    results = [
        MatchResult("Team A", "Team B", 2, 1, "PL", datetime(2026, 1, 1)),
        MatchResult("Team B", "Team A", 1, 1, "PL", datetime(2026, 1, 8)),
    ]
    model = CalibratedPoissonModel()
    model.calibrate(results)
    pred = model.predict_match("Unknown FC", "Mystery United", "EPL")
    assert pred.prob_home_win > 0
    assert pred.prob_away_win > 0
