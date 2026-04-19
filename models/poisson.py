"""Poisson goal model for football matches.

This is a classic approach: estimate expected goals for home/away teams,
assume goals follow independent Poisson distributions, and derive
scoreline/outcome probabilities.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class PoissonParams:
    lambda_home: float
    lambda_away: float


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def scoreline_probs(params: PoissonParams, max_goals: int = 10) -> Dict[Tuple[int, int], float]:
    """Return a dict mapping (home_goals, away_goals) -> probability."""

    probs: Dict[Tuple[int, int], float] = {}
    for hg in range(0, max_goals + 1):
        for ag in range(0, max_goals + 1):
            p = poisson_pmf(hg, params.lambda_home) * poisson_pmf(ag, params.lambda_away)
            probs[(hg, ag)] = p
    return probs


def outcome_probs(params: PoissonParams, max_goals: int = 10) -> Dict[str, float]:
    """Aggregate scoreline probabilities into 1X2 outcome probs."""

    probs = scoreline_probs(params, max_goals=max_goals)
    home = 0.0
    draw = 0.0
    away = 0.0
    for (hg, ag), p in probs.items():
        if hg > ag:
            home += p
        elif hg == ag:
            draw += p
        else:
            away += p
    return {"HOME": home, "DRAW": draw, "AWAY": away}
