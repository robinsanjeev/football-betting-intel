"""Hybrid model combining Poisson features with a ML regressor.

This module wires up a feature-generation pipeline based on Poisson
parameters and a generic regressor interface (e.g., XGBoost). The actual
model training/loading is left to a separate script, but the interface is
ready to plug in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol

from .poisson import PoissonParams, outcome_probs


class Regressor(Protocol):
    """Protocol for ML regressors used in the hybrid model.

    This mirrors the scikit-learn / XGBoost-style predict_proba interface.
    """

    def predict_proba(self, X: Any) -> Any:  # pragma: no cover - interface stub
        ...


@dataclass
class HybridModel:
    regressor: Regressor

    def _build_features(self, params: PoissonParams) -> Dict[str, float]:
        base = outcome_probs(params)
        # Simple feature set for now; can be extended with form, injuries, rest, etc.
        return {
            "p_home_poisson": base["HOME"],
            "p_draw_poisson": base["DRAW"],
            "p_away_poisson": base["AWAY"],
        }

    def predict_outcome_probs(self, params: PoissonParams) -> Dict[str, float]:
        """Predict 1X2 probabilities using Poisson-derived features + regressor."""

        feats = self._build_features(params)
        X = [[feats["p_home_poisson"], feats["p_draw_poisson"], feats["p_away_poisson"]]]
        proba = self.regressor.predict_proba(X)[0]
        # Assume order [HOME, DRAW, AWAY]
        return {"HOME": float(proba[0]), "DRAW": float(proba[1]), "AWAY": float(proba[2])}
