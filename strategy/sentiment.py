"""Market sentiment helpers based on Kalshi order book depth.

We compute a simple "crowd vs model" metric by comparing order-book-implied
probabilities to model probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class SentimentResult:
    implied_prob: float
    model_prob: float
    crowd_vs_model: float


def compute_crowd_vs_model(implied_prob: float, model_prob: float) -> SentimentResult:
    """Return a simple sentiment delta: positive if crowd is more bullish than model."""

    return SentimentResult(
        implied_prob=implied_prob,
        model_prob=model_prob,
        crowd_vs_model=implied_prob - model_prob,
    )
