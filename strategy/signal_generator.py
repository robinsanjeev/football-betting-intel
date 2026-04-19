"""EV signal generator: compare model predictions against Kalshi prices.

For each upcoming match on Kalshi, the SignalGenerator:
  1. Gets a MatchPrediction from the CalibratedPoissonModel
  2. Iterates through every market in the SoccerMatch
  3. Emits a BettingSignal for any market where our model probability
     exceeds the Kalshi-implied probability by at least `min_edge`

EV per dollar formula (for a Kalshi Yes contract at price P):
  EV = model_prob * (1 - P) - (1 - model_prob) * P
     = model_prob - P
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from football_intel.common.logging_utils import get_logger
from football_intel.ingestion.kalshi_soccer import SoccerMarket, SoccerMatch
from football_intel.models.calibrated_poisson import CalibratedPoissonModel, MatchPrediction
# Adaptive params — imported lazily to avoid circular imports at module load time
# The actual import happens inside __init__ and reload_adaptive_params

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class BettingSignal:
    """A single positive-edge betting opportunity."""

    event_ticker: str        # Kalshi event ticker for the match
    match_title: str          # "Chelsea vs Man Utd"
    competition: str          # "EPL"
    bet_type: str             # "MONEYLINE", "OVER_UNDER", "SPREAD", "BTTS", "FIRST_HALF"
    market_ticker: str        # Kalshi market ticker
    description: str          # human-readable: "Chelsea to win", "Over 2.5 goals"
    model_prob: float         # our model's probability (0-1)
    kalshi_implied_prob: float  # Kalshi's implied probability from yes_ask
    edge: float               # model_prob - kalshi_implied_prob
    ev_per_dollar: float      # EV per $1 bet on the Yes contract
    confidence: str           # "HIGH" / "MEDIUM" / "LOW"
    kalshi_url: str           # https://kalshi.com/markets/{ticker}
    kalshi_odds: float = 0.0  # 1.0 / kalshi_implied_prob (decimal odds)
    reasoning: str = ""       # qualitative explanation for the signal
    # ── New calibration fields (added for better risk management) ──────
    raw_model_prob: float = 0.0   # original model prob before market shrinkage
    suggested_fraction: float = 1.0  # recommended bet fraction: HIGH=1.0, MED=0.5, LOW=0.25


# ---------------------------------------------------------------------------
# Confidence helper
# ---------------------------------------------------------------------------

def _confidence(home_matches: int, away_matches: int) -> str:
    """Rate confidence based on how much historical data we have.

    HIGH   → min(home, away) >= 20 matches
    MEDIUM → min(home, away) >= 10 matches
    LOW    → less than 10 matches for at least one team
    """
    m = min(home_matches, away_matches)
    if m >= 20:
        return "HIGH"
    if m >= 10:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# Market-to-model mapping helpers
# ---------------------------------------------------------------------------

def _get_model_prob_for_market(
    market: SoccerMarket,
    prediction: MatchPrediction,
) -> Optional[Tuple[float, str]]:
    """Return (model_probability, description) for a given market.

    Returns None if this market type is not handled or cannot be mapped.
    """
    bet_type = market.bet_type
    line = market.line
    side = market.side

    # ── MONEYLINE ──────────────────────────────────────────────────────
    if bet_type == "MONEYLINE":
        if side == "HOME":
            return prediction.prob_home_win, f"{prediction.home_team} to win"
        if side == "DRAW":
            return prediction.prob_draw, "Draw"
        if side == "AWAY":
            return prediction.prob_away_win, f"{prediction.away_team} to win"
        # If side is not resolved, try to infer from yes_sub_title
        sub = (market.yes_sub_title or "").lower()
        if "draw" in sub or "tie" in sub:
            return prediction.prob_draw, "Draw"
        if prediction.home_team.lower() in sub:
            return prediction.prob_home_win, f"{prediction.home_team} to win"
        if prediction.away_team.lower() in sub:
            return prediction.prob_away_win, f"{prediction.away_team} to win"
        return None

    # ── OVER_UNDER (totals) ────────────────────────────────────────────
    if bet_type == "OVER_UNDER":
        if line is None:
            return None
        # Check if the market is for "Over X.5" or "Under X.5"
        # We handle Over markets directly; for Under markets, invert.
        sub = (market.yes_sub_title or market.market_title or "").lower()
        is_over = "over" in sub or "o" + str(line) in sub.replace(" ", "")
        is_under = "under" in sub or "u" + str(line) in sub.replace(" ", "")

        # Default: assume Yes = Over (most common Kalshi convention)
        if not is_under:
            is_over = True

        if abs(line - 1.5) < 0.01:
            model_p = prediction.prob_over_1_5
        elif abs(line - 2.5) < 0.01:
            model_p = prediction.prob_over_2_5
        elif abs(line - 3.5) < 0.01:
            model_p = prediction.prob_over_3_5
        elif abs(line - 4.5) < 0.01:
            model_p = prediction.prob_over_4_5
        else:
            return None  # line not supported

        if is_under:
            model_p = 1.0 - model_p
            desc = f"Under {line} goals"
        else:
            desc = f"Over {line} goals"

        return model_p, desc

    # ── BTTS ───────────────────────────────────────────────────────────
    if bet_type == "BTTS":
        sub = (market.yes_sub_title or "").lower()
        # Yes = both teams score
        if "yes" in sub or "both" in sub or not ("no" in sub):
            return prediction.prob_btts_yes, "Both teams to score (Yes)"
        else:
            return 1.0 - prediction.prob_btts_yes, "Both teams to score (No)"

    # ── SPREAD ─────────────────────────────────────────────────────────
    if bet_type == "SPREAD":
        if line is None:
            return None
        sub = (market.yes_sub_title or "").lower()
        home_lower = prediction.home_team.lower()
        away_lower = prediction.away_team.lower()

        # Determine which team the spread is for
        is_home = (
            side == prediction.home_team
            or (side == "HOME")
            or (home_lower and home_lower in sub)
        )
        is_away = (
            side == prediction.away_team
            or (side == "AWAY")
            or (away_lower and away_lower in sub)
        )

        # Spread line: "Team wins by more than X.5" → team wins by X+1 goals
        # line=1.5 → team wins by 2+
        # line=2.5 → team wins by 3+
        if is_home and not is_away:
            if abs(line - 1.5) < 0.01:
                return prediction.prob_home_spread_1_5, f"{prediction.home_team} wins by 2+"
            if abs(line - 2.5) < 0.01:
                return prediction.prob_home_spread_2_5, f"{prediction.home_team} wins by 3+"
        elif is_away and not is_home:
            if abs(line - 1.5) < 0.01:
                return prediction.prob_away_spread_1_5, f"{prediction.away_team} wins by 2+"
            if abs(line - 2.5) < 0.01:
                return prediction.prob_away_spread_2_5, f"{prediction.away_team} wins by 3+"
        return None

    # ── FIRST_HALF ─────────────────────────────────────────────────────
    if bet_type == "FIRST_HALF":
        sub = (market.yes_sub_title or "").lower()
        home_lower = prediction.home_team.lower()
        away_lower = prediction.away_team.lower()

        if "draw" in sub or "tie" in sub:
            return prediction.prob_first_half_draw, "First half draw"
        if home_lower and home_lower in sub:
            return prediction.prob_first_half_home, f"{prediction.home_team} leads at HT"
        if away_lower and away_lower in sub:
            return prediction.prob_first_half_away, f"{prediction.away_team} leads at HT"
        if "home" in sub:
            return prediction.prob_first_half_home, f"{prediction.home_team} leads at HT"
        if "away" in sub:
            return prediction.prob_first_half_away, f"{prediction.away_team} leads at HT"
        return None

    # Unknown bet type
    return None


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------

class SignalGenerator:
    """Compare model predictions against Kalshi prices to find +EV bets.

    Args:
        model: A calibrated CalibratedPoissonModel instance.
    """

    # Maximum credible edge — signals beyond this are almost certainly model error
    _MAX_EDGE: float = 0.25
    # Bet-sizing fractions by confidence tier
    _SIZING = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.25}

    def __init__(self, model: CalibratedPoissonModel) -> None:
        self.model = model
        self._adaptive_params = None
        self.reload_adaptive_params()

    def reload_adaptive_params(self) -> None:
        """Load (or reload) adaptive parameters from the JSON store.

        Safe to call at any time — falls back to None (hardcoded defaults)
        if the file is missing or corrupt.
        """
        try:
            from football_intel.strategy.adaptive import AdaptiveAnalyzer
            analyzer = AdaptiveAnalyzer()
            self._adaptive_params = analyzer.load_params()
            logger.debug(
                "Loaded adaptive params v%d (sample_size=%d)",
                self._adaptive_params.version,
                self._adaptive_params.sample_size,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load adaptive params: %s — using hardcoded defaults", exc)
            self._adaptive_params = None

    def _shrink_toward_market(
        self,
        model_prob: float,
        market_prob: float,
        confidence: str,
    ) -> float:
        """Blend model probability toward the market to reduce overconfidence.

        When the model diverges from an efficient market, the market is often
        incorporating information the model doesn't have.  We trust our model
        more when we have lots of historical data (HIGH) and less when we
        don't (LOW).  Alpha values are loaded from adaptive params when available.

        Args:
            model_prob:  Raw model probability.
            market_prob: Kalshi implied probability.
            confidence:  "HIGH" / "MEDIUM" / "LOW" (from historical data volume).

        Returns:
            Adjusted probability blended toward market.
        """
        # Prefer adaptive alpha if available
        if self._adaptive_params is not None:
            alpha = self._adaptive_params.shrinkage_alpha_by_conf.get(confidence, 0.5)
        else:
            alpha_map = {"HIGH": 0.7, "MEDIUM": 0.5, "LOW": 0.3}
            alpha = alpha_map.get(confidence, 0.5)
        return alpha * model_prob + (1.0 - alpha) * market_prob

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_signals(
        self,
        matches: List[SoccerMatch],
        min_edge: float = 0.08,
    ) -> List[BettingSignal]:
        """Compare model predictions against Kalshi prices for all matches.

        Args:
            matches: List of SoccerMatch objects from KalshiSoccerClient.
            min_edge: Minimum edge (model_prob - kalshi_implied_prob) required
                      to emit a signal. Used as a fallback when adaptive params
                      are not available or do not specify a type-specific threshold.
                      Default 0.08 = 8%.

        Returns:
            List of BettingSignal objects where edge > min_edge, sorted by
            ev_per_dollar descending.
        """
        all_signals: List[BettingSignal] = []

        # Determine which confidence levels are allowed
        if self._adaptive_params is not None:
            allowed_confidence = set(self._adaptive_params.enabled_confidence)
            allowed_bet_types = set(self._adaptive_params.enabled_bet_types)
        else:
            allowed_confidence = {"HIGH", "MEDIUM", "LOW"}
            allowed_bet_types = {"MONEYLINE", "OVER_UNDER", "BTTS", "SPREAD", "FIRST_HALF"}

        for match in matches:
            try:
                prediction = self.model.predict_from_kalshi_match(match)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "signal_generator: could not predict %s vs %s (%s): %s",
                    match.home_team, match.away_team, match.competition, exc,
                )
                continue

            signals = self._match_prediction_to_signals(
                match, prediction, min_edge,
                allowed_confidence=allowed_confidence,
                allowed_bet_types=allowed_bet_types,
            )
            all_signals.extend(signals)

        # Sort by EV descending
        all_signals.sort(key=lambda s: s.ev_per_dollar, reverse=True)
        return all_signals

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_reasoning(signal: BettingSignal) -> str:
        """Generate a qualitative explanation for a BettingSignal.

        Includes shrinkage notes, edge-cap warnings, and sizing hints.
        """
        parts: List[str] = []

        # ── Confidence prefix ──────────────────────────────────────────
        if signal.confidence == "HIGH":
            parts.append("Strong historical data backs this pick.")
        elif signal.confidence == "MEDIUM":
            parts.append("Decent sample size; model has reasonable certainty.")
        else:
            parts.append("Limited data — treat as speculative.")

        # ── Shrinkage note ─────────────────────────────────────────────
        if signal.raw_model_prob > 0 and abs(signal.model_prob - signal.raw_model_prob) > 0.01:
            parts.append(
                f"Raw model: {signal.raw_model_prob:.0%}; "
                f"adjusted toward market: {signal.model_prob:.0%}."
            )

        # ── Bet-type context ───────────────────────────────────────────
        if signal.bet_type == "MONEYLINE":
            parts.append(
                f"Our model gives {signal.description} a {signal.model_prob:.0%} chance, "
                f"vs the market's {signal.kalshi_implied_prob:.0%}."
            )
        elif signal.bet_type == "OVER_UNDER":
            parts.append(
                f"Goal-rate model puts {signal.description} at {signal.model_prob:.0%}, "
                f"market prices it at {signal.kalshi_implied_prob:.0%}."
            )
        elif signal.bet_type == "BTTS":
            parts.append(
                f"Both-teams-to-score model: {signal.model_prob:.0%} vs market {signal.kalshi_implied_prob:.0%}."
            )
        elif signal.bet_type == "SPREAD":
            parts.append(
                f"Spread model favours {signal.description} at {signal.model_prob:.0%} "
                f"vs market {signal.kalshi_implied_prob:.0%}."
            )
        elif signal.bet_type == "FIRST_HALF":
            parts.append(
                f"Half-time model gives {signal.description} a {signal.model_prob:.0%} chance "
                f"vs market {signal.kalshi_implied_prob:.0%}."
            )

        # ── Win probability context ──────────────────────────────────
        if signal.model_prob >= 0.60:
            parts.append(f"Win likelihood: {signal.model_prob:.0%} — strong favourite.")
        elif signal.model_prob >= 0.40:
            parts.append(f"Win likelihood: {signal.model_prob:.0%} — competitive odds.")
        elif signal.model_prob >= 0.25:
            parts.append(f"Win likelihood: {signal.model_prob:.0%} — moderate risk.")
        else:
            parts.append(f"Win likelihood: {signal.model_prob:.0%} — higher risk, bet small.")

        # ── Edge commentary ────────────────────────────────────────────
        # Note: signal.edge is already capped at _MAX_EDGE
        raw_edge = signal.model_prob - signal.kalshi_implied_prob
        if raw_edge > SignalGenerator._MAX_EDGE:
            parts.append(
                f"Edge capped at {SignalGenerator._MAX_EDGE:.0%} — "
                "extreme divergence from market suggests model uncertainty."
            )
        elif signal.edge >= 0.20:
            parts.append("Very large edge — high-confidence opportunity.")
        elif signal.edge >= 0.10:
            parts.append("Solid edge over the market.")
        else:
            parts.append("Marginal edge; bet small.")

        # ── Sizing hint ────────────────────────────────────────────────
        frac = signal.suggested_fraction
        if frac < 1.0:
            parts.append(f"Suggested size: {frac:.0%} of a standard unit.")

        return " ".join(parts)

    def _match_prediction_to_signals(
        self,
        match: SoccerMatch,
        prediction: MatchPrediction,
        min_edge: float,
        allowed_confidence: Optional[set] = None,
        allowed_bet_types: Optional[set] = None,
    ) -> List[BettingSignal]:
        """For a single match, compare each Kalshi market to the model.

        Args:
            match: SoccerMatch with all its markets.
            prediction: The model's MatchPrediction for this fixture.
            min_edge: Minimum edge threshold (used as fallback).
            allowed_confidence: Set of confidence levels to include.
            allowed_bet_types: Set of bet types to include.

        Returns:
            List of BettingSignal objects for this match.
        """
        if allowed_confidence is None:
            allowed_confidence = {"HIGH", "MEDIUM", "LOW"}
        if allowed_bet_types is None:
            allowed_bet_types = {"MONEYLINE", "OVER_UNDER", "BTTS", "SPREAD", "FIRST_HALF"}
        signals: List[BettingSignal] = []
        match_title = f"{match.home_team} vs {match.away_team}"
        conf = _confidence(prediction.home_team_matches, prediction.away_team_matches)
        suggested_fraction = self._SIZING.get(conf, 0.5)

        # Skip if confidence level is disabled by adaptive params
        if conf not in allowed_confidence:
            return signals

        for market in match.markets:
            # Skip markets with no Kalshi price
            if market.implied_prob_yes is None or market.implied_prob_yes <= 0:
                continue

            # Skip disabled bet types
            if market.bet_type not in allowed_bet_types:
                continue

            result = _get_model_prob_for_market(market, prediction)
            if result is None:
                continue

            raw_model_prob, description = result
            kalshi_p = market.implied_prob_yes

            # ── Market-aware shrinkage ─────────────────────────────────
            model_prob = self._shrink_toward_market(raw_model_prob, kalshi_p, conf)

            edge = model_prob - kalshi_p

            # ── Per-type min_edge from adaptive params (fallback to arg) ─
            if self._adaptive_params is not None:
                effective_min_edge = self._adaptive_params.min_edge_by_type.get(
                    market.bet_type, min_edge
                )
            else:
                effective_min_edge = min_edge

            if edge <= effective_min_edge:
                continue

            # ── Minimum win probability filter (adaptive or hardcoded) ──
            if self._adaptive_params is not None:
                min_prob = self._adaptive_params.min_prob_by_type.get(
                    market.bet_type, 0.15
                )
            else:
                min_prob = 0.15

            if model_prob < min_prob:
                continue

            # ── Edge cap (25%) ─────────────────────────────────────────
            edge_capped = min(edge, self._MAX_EDGE)

            # EV per $1 on the Yes contract (probability-adjusted)
            # Buy Yes at price P: win → profit (1-P), lose → lose P
            # EV = model_prob * (1-P) - (1-model_prob) * P
            ev_per_dollar = model_prob * (1.0 - kalshi_p) - (1.0 - model_prob) * kalshi_p

            # Build Kalshi URL
            event_ticker = match.event_ticker
            url_parts = event_ticker.split('-')
            series_ticker = url_parts[0] if url_parts else event_ticker
            kalshi_url = f"https://kalshi.com/markets/{series_ticker}/{event_ticker}"

            kalshi_odds = (1.0 / kalshi_p) if kalshi_p > 0 else 0.0

            signal = BettingSignal(
                event_ticker=event_ticker,
                match_title=match_title,
                competition=match.competition,
                bet_type=market.bet_type,
                market_ticker=market.market_ticker,
                description=description,
                model_prob=model_prob,
                kalshi_implied_prob=kalshi_p,
                edge=edge_capped,
                ev_per_dollar=ev_per_dollar,
                confidence=conf,
                kalshi_url=kalshi_url,
                kalshi_odds=kalshi_odds,
                raw_model_prob=raw_model_prob,
                suggested_fraction=suggested_fraction,
            )
            signal.reasoning = self._generate_reasoning(signal)
            signals.append(signal)

        return signals
