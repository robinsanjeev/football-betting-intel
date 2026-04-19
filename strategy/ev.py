"""Expected Value (EV) calculation utilities for betting strategies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EVResult:
    probability_win: float
    probability_lose: float
    potential_profit: float
    stake: float
    ev: float


def implied_prob_from_price(price: float) -> float:
    """Convert a Kalshi-style "yes" contract price (0-1 or 0-100) to implied prob.

    This is intentionally simple; adjust based on actual Kalshi pricing
    semantics (e.g., fees, payouts).
    """

    if price <= 1.0:
        return price
    return price / 100.0


def expected_value(prob_win: float, potential_profit: float, stake: float) -> EVResult:
    prob_lose = 1.0 - prob_win
    ev = (prob_win * potential_profit) - (prob_lose * stake)
    return EVResult(
        probability_win=prob_win,
        probability_lose=prob_lose,
        potential_profit=potential_profit,
        stake=stake,
        ev=ev,
    )


def should_bet(ev_result: EVResult) -> bool:
    """Return True if EV > 0 (positive edge)."""

    return ev_result.ev > 0.0
