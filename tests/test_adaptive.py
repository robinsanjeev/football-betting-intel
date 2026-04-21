"""Basic tests for the adaptive feedback loop."""
from football_intel.strategy.adaptive import AdaptiveAnalyzer, AdaptiveParams


def test_load_params_returns_defaults_when_no_file():
    """Should return default params when JSON doesn't exist."""
    analyzer = AdaptiveAnalyzer()
    params = analyzer.load_params()
    assert params is not None
    assert params.version >= 0


def test_compute_optimal_params_with_empty_data():
    """Should handle zero settled trades gracefully."""
    analyzer = AdaptiveAnalyzer()
    analysis = analyzer.analyze_settled_trades()
    params = analyzer.compute_optimal_params(analysis)
    assert params is not None
    assert isinstance(params.min_edge_by_type, dict)
