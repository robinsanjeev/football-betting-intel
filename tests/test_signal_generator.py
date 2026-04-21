"""Basic tests for signal generation."""
from football_intel.strategy.signal_generator import SignalGenerator, BettingSignal
from football_intel.models.calibrated_poisson import CalibratedPoissonModel
from football_intel.models.historical_data import MatchResult
from datetime import datetime


def _make_calibrated_model():
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
    return model


def test_signal_generator_initializes():
    model = _make_calibrated_model()
    gen = SignalGenerator(model)
    assert gen is not None


def test_min_edge_filters():
    """Signals with edge below threshold should be filtered out."""
    model = _make_calibrated_model()
    gen = SignalGenerator(model)
    # With impossibly high min_edge, should get no signals
    signals = gen.generate_signals([], min_edge=0.99)
    assert len(signals) == 0


def test_betting_signal_has_required_fields():
    """BettingSignal should have all expected fields."""
    sig = BettingSignal(
        event_ticker="TEST",
        match_title="A vs B",
        competition="EPL",
        bet_type="MONEYLINE",
        market_ticker="TEST-MKT",
        description="A to win",
        model_prob=0.6,
        kalshi_implied_prob=0.4,
        edge=0.2,
        ev_per_dollar=0.2,
        confidence="HIGH",
        kalshi_url="https://kalshi.com/test",
    )
    assert sig.edge == 0.2
    assert sig.model_prob == 0.6
    assert sig.suggested_fraction == 1.0  # default
