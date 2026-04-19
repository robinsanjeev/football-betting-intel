"""Calibrated Poisson goal model for soccer betting.

Builds on the naive Poisson model (models/poisson.py) by estimating
per-team attack and defence strengths from historical results, then
using those to compute calibrated expected-goals (lambda) values for
any upcoming fixture.

Usage
-----
    from football_intel.models.calibrated_poisson import CalibratedPoissonModel
    from football_intel.models.historical_data import load_historical_results

    results = load_historical_results()           # fetches/loads cache
    model = CalibratedPoissonModel()
    model.calibrate(results)
    pred = model.predict_match("Chelsea FC", "Arsenal FC", "PL")
    print(pred.prob_home_win, pred.prob_draw, pred.prob_away_win)
"""

from __future__ import annotations

import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from football_intel.common.logging_utils import get_logger
from football_intel.models.historical_data import MatchResult, load_historical_results
from football_intel.models.poisson import poisson_pmf, scoreline_probs, PoissonParams
from football_intel.ingestion.kalshi_soccer import SoccerMatch, SoccerMarket

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Team name alias table
# ---------------------------------------------------------------------------
# Maps a canonical football-data.org name (or normalised form) to a list of
# alternative spellings used by Kalshi and other sources.
# Keys should be lower-cased; matching is done case-insensitively.
#
# Format: { "canonical_fd_name_lower": ["alias1", "alias2", ...] }
# The canonical name is what football-data.org returns (without "FC"/"AFC").

TEAM_ALIASES: Dict[str, List[str]] = {
    # ── Premier League ──────────────────────────────────────────────────
    "arsenal fc":               ["arsenal"],
    "aston villa fc":           ["aston villa", "villa"],
    "bournemouth":              ["afc bournemouth", "bournemouth"],
    "brentford fc":             ["brentford"],
    "brighton & hove albion fc":["brighton", "brighton & hove albion", "brighton hove albion"],
    "chelsea fc":               ["chelsea"],
    "crystal palace fc":        ["crystal palace"],
    "everton fc":               ["everton"],
    "fulham fc":                ["fulham"],
    "ipswich town fc":          ["ipswich", "ipswich town"],
    "leicester city fc":        ["leicester", "leicester city"],
    "liverpool fc":             ["liverpool"],
    "manchester city fc":       ["man city", "manchester city"],
    "manchester united fc":     ["man utd", "man united", "manchester united", "manchester utd"],
    "newcastle united fc":      ["newcastle", "newcastle united", "newcastle utd"],
    "nottingham forest fc":     ["nottingham forest", "notts forest", "nott'm forest"],
    "southampton fc":           ["southampton"],
    "tottenham hotspur fc":     ["tottenham", "spurs", "tottenham hotspur"],
    "west ham united fc":       ["west ham", "west ham united"],
    "wolverhampton wanderers fc":["wolves", "wolverhampton", "wolverhampton wanderers"],

    # ── Bundesliga ──────────────────────────────────────────────────────
    "fc bayern münchen":        ["bayern", "bayern munich", "fc bayern", "bay munich"],
    "borussia dortmund":        ["dortmund", "bvb"],
    "bayer 04 leverkusen":      ["leverkusen", "bayer leverkusen", "bayer 04"],
    "rb leipzig":               ["leipzig", "rb leipzig", "rasenballsport leipzig"],
    "eintracht frankfurt":      ["frankfurt", "ein frankfurt"],
    "vfb stuttgart":            ["stuttgart"],
    "sc freiburg":              ["freiburg"],
    "tsg 1899 hoffenheim":      ["hoffenheim", "tsg hoffenheim"],
    "1. fc union berlin":       ["union berlin", "fc union berlin"],
    "borussia mönchengladbach": ["mönchengladbach", "gladbach", "monchengladbach", "m'gladbach"],
    "1. fsv mainz 05":          ["mainz", "mainz 05", "fsv mainz"],
    "fc augsburg":              ["augsburg"],
    "1. fc köln":               ["köln", "koln", "fc köln", "fc koln", "cologne"],
    "vfl wolfsburg":            ["wolfsburg"],
    "sv werder bremen":         ["werder bremen", "werder", "bremen"],
    "fc st. pauli":             ["st pauli", "st. pauli"],
    "holstein kiel":            ["kiel"],
    "vfl bochum 1848":          ["bochum"],
    "heidenheimer sb":          ["heidenheim"],
    "hamburger sv":             ["hamburger sv", "hsv", "hamburg"],

    # ── Champions League / UCL (teams not already listed above) ─────────
    "real madrid cf":           ["real madrid"],
    "fc barcelona":             ["barcelona", "barca"],
    "atletico de madrid":       ["atletico madrid", "atletico", "atlético madrid"],
    "sevilla fc":               ["sevilla"],
    "villarreal cf":            ["villarreal"],
    "athletic club":            ["athletic bilbao", "athletic club bilbao"],
    "real sociedad de fútbol":  ["real sociedad"],
    "inter milan":              ["inter milan", "internazionale", "inter"],
    "ac milan":                 ["ac milan", "milan"],
    "juventus fc":              ["juventus", "juve"],
    "ssc napoli":               ["napoli"],
    "as roma":                  ["roma"],
    "ss lazio":                 ["lazio"],
    "atalanta bc":              ["atalanta"],
    "psg":                      ["paris saint-germain", "paris sg", "paris saint germain"],
    "paris saint-germain fc":   ["psg", "paris sg", "paris saint germain"],
    "olympique de marseille":   ["marseille"],
    "olympique lyonnais":       ["lyon", "olympique lyonnais"],
    "as monaco fc":             ["monaco", "as monaco"],
    "lille osc":                ["lille"],
    "ajax":                     ["ajax amsterdam", "afc ajax"],
    "psv eindhoven":            ["psv"],
    "feyenoord":                ["feyenoord rotterdam"],
    "sporting cp":              ["sporting lisbon", "sporting clube de portugal"],
    "fc porto":                 ["porto"],
    "sl benfica":               ["benfica"],
    "fc celtic":                ["celtic"],
    "rangers fc":               ["rangers"],
    "shakhtar donetsk":         ["shakhtar"],
    "fc red bull salzburg":     ["rb salzburg", "red bull salzburg", "salzburg"],
    "bsc young boys":           ["young boys"],
    "fc zürich":                ["zurich", "fc zurich"],
    "fc dinamo kyiv":           ["dynamo kyiv", "dynamo kiev"],
    "club brugge kv":           ["club brugge", "brugge"],
    "rsc anderlecht":           ["anderlecht"],
    "celtic fc":                ["celtic"],
    "benfica":                  ["sl benfica", "sport lisboa e benfica"],
    "ac sporting":              ["sporting"],
    "as monaco":                ["monaco"],
}

# Pre-build a flat lookup: normalised_alias → canonical_fd_name
_ALIAS_LOOKUP: Dict[str, str] = {}
for _canonical, _aliases in TEAM_ALIASES.items():
    _ALIAS_LOOKUP[_canonical.lower()] = _canonical  # canonical maps to itself
    for _a in _aliases:
        _ALIAS_LOOKUP[_a.lower()] = _canonical


def normalise_team_name(name: str) -> str:
    """Return the canonical football-data.org team name for any alias.

    First tries exact match (case-insensitive) in the alias table; falls
    back to SequenceMatcher fuzzy matching against all known names; if still
    no confident match, returns the original name stripped of common suffixes.

    Args:
        name: Team name as it appears in any source (Kalshi, football-data.org, etc.)

    Returns:
        Best-matching canonical name, or the input name if nothing fits.
    """
    if not name:
        return name

    lower = name.strip().lower()

    # Direct alias lookup
    if lower in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[lower]

    # Also try stripping "FC", "AFC", "SC", "CF", "SV" suffixes/prefixes
    stripped = (
        lower
        .removeprefix("fc ").removeprefix("afc ").removeprefix("sc ")
        .removesuffix(" fc").removesuffix(" afc").removesuffix(" sc")
        .removesuffix(" cf").removesuffix(" sv").removesuffix(" kv")
        .strip()
    )
    if stripped in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[stripped]

    # Fuzzy fallback using SequenceMatcher
    best_ratio = 0.0
    best_name = name
    all_keys = list(_ALIAS_LOOKUP.keys())
    for key in all_keys:
        ratio = SequenceMatcher(None, lower, key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_name = _ALIAS_LOOKUP[key]

    if best_ratio >= 0.72:  # threshold: ~72% similarity required
        logger.debug(
            "normalise_team_name: fuzzy match '%s' → '%s' (ratio=%.2f)",
            name, best_name, best_ratio,
        )
        return best_name

    # Give up — return original (will fall back to league-average in model)
    logger.debug("normalise_team_name: no match for '%s'", name)
    return name


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TeamStrength:
    """Per-team calibration parameters (all relative to league average = 1.0)."""
    attack_home: float    # goals scored at home / league avg home goals
    attack_away: float    # goals scored away / league avg away goals
    defense_home: float   # goals conceded at home / league avg away goals
    defense_away: float   # goals conceded away / league avg home goals
    matches_played: int   # total matches in the calibration window


@dataclass
class LeagueStats:
    """League-wide calibration statistics for a single competition."""
    avg_home_goals: float          # average home-team goals per match in this league
    avg_away_goals: float          # average away-team goals per match in this league
    team_strengths: Dict[str, TeamStrength]  # canonical name → strength


@dataclass
class MatchPrediction:
    """Full probability prediction for a single match."""
    home_team: str
    away_team: str
    competition: str
    lambda_home: float   # expected home goals
    lambda_away: float   # expected away goals

    # 1X2
    prob_home_win: float
    prob_draw: float
    prob_away_win: float

    # Totals (over N.5 goals in the match)
    prob_over_1_5: float
    prob_over_2_5: float
    prob_over_3_5: float
    prob_over_4_5: float

    # Both teams to score
    prob_btts_yes: float

    # Asian handicap spreads
    prob_home_spread_1_5: float  # home wins by 2+ (spread -1.5 for home)
    prob_home_spread_2_5: float  # home wins by 3+ (spread -2.5 for home)
    prob_away_spread_1_5: float  # away wins by 2+
    prob_away_spread_2_5: float  # away wins by 3+

    # First-half approximations (~45% of full-match lambdas)
    prob_first_half_home: float
    prob_first_half_draw: float
    prob_first_half_away: float

    # Data confidence (lower bound across both teams)
    home_team_matches: int
    away_team_matches: int


# ---------------------------------------------------------------------------
# Dixon-Coles low-score correction
# ---------------------------------------------------------------------------

# Small positive rho: draws and low-scoring results are slightly more likely
# than a pure Poisson model predicts.  Typical published values: 0.03–0.08.
_DIXON_COLES_RHO: float = 0.04


def _apply_dixon_coles_correction(
    matrix: Dict[Tuple[int, int], float],
    lambda_home: float,
    lambda_away: float,
    rho: float = _DIXON_COLES_RHO,
) -> Dict[Tuple[int, int], float]:
    """Apply Dixon-Coles (1997) low-score correlation correction.

    Adjusts P(0,0), P(1,0), P(0,1), and P(1,1) to account for the empirical
    observation that near-draws are slightly more common than a pure
    independence assumption predicts.  The matrix is renormalised after the
    correction so all probabilities still sum to 1.

    Args:
        matrix:       Raw scoreline probability dict from Poisson PMFs.
        lambda_home:  Expected home goals.
        lambda_away:  Expected away goals.
        rho:          Correlation parameter (positive → draws/low-scores more likely).

    Returns:
        Corrected and renormalised probability dict.
    """
    corrected = dict(matrix)

    if (0, 0) in corrected:
        corrected[(0, 0)] *= 1.0 + rho * lambda_home * lambda_away
    if (1, 0) in corrected:
        corrected[(1, 0)] *= 1.0 - rho * lambda_away
    if (0, 1) in corrected:
        corrected[(0, 1)] *= 1.0 - rho * lambda_home
    if (1, 1) in corrected:
        corrected[(1, 1)] *= 1.0 + rho

    # Renormalise
    total = sum(corrected.values())
    if total > 0:
        corrected = {k: v / total for k, v in corrected.items()}

    return corrected


# ---------------------------------------------------------------------------
# Helper: scoreline matrix with given lambdas
# ---------------------------------------------------------------------------

def _compute_scoreline_matrix(
    lambda_home: float,
    lambda_away: float,
    max_goals: int = 10,
) -> Dict[Tuple[int, int], float]:
    """Build a (home_goals, away_goals) → probability dict using Poisson PMFs.

    Applies a Dixon-Coles low-score correlation correction so that 0-0, 1-0,
    0-1, and 1-1 scorelines are modelled more accurately than a pure
    independent Poisson assumption allows.
    """
    params = PoissonParams(lambda_home=lambda_home, lambda_away=lambda_away)
    matrix = scoreline_probs(params, max_goals=max_goals)
    return _apply_dixon_coles_correction(matrix, lambda_home, lambda_away)


def _derive_probabilities(
    lambda_home: float,
    lambda_away: float,
    home_team: str,
    away_team: str,
    competition: str,
    home_matches: int,
    away_matches: int,
) -> MatchPrediction:
    """Compute all market probabilities from two lambda values."""
    matrix = _compute_scoreline_matrix(lambda_home, lambda_away)

    # 1X2
    prob_home_win = sum(p for (h, a), p in matrix.items() if h > a)
    prob_draw     = sum(p for (h, a), p in matrix.items() if h == a)
    prob_away_win = sum(p for (h, a), p in matrix.items() if h < a)

    # Total goals
    prob_over_1_5 = sum(p for (h, a), p in matrix.items() if h + a > 1)
    prob_over_2_5 = sum(p for (h, a), p in matrix.items() if h + a > 2)
    prob_over_3_5 = sum(p for (h, a), p in matrix.items() if h + a > 3)
    prob_over_4_5 = sum(p for (h, a), p in matrix.items() if h + a > 4)

    # BTTS: both teams score at least 1
    prob_btts_yes = sum(p for (h, a), p in matrix.items() if h >= 1 and a >= 1)

    # Spreads
    prob_home_spread_1_5 = sum(p for (h, a), p in matrix.items() if h - a >= 2)
    prob_home_spread_2_5 = sum(p for (h, a), p in matrix.items() if h - a >= 3)
    prob_away_spread_1_5 = sum(p for (h, a), p in matrix.items() if a - h >= 2)
    prob_away_spread_2_5 = sum(p for (h, a), p in matrix.items() if a - h >= 3)

    # First half: scale lambdas by 0.45 (roughly 45% of goals happen in first half)
    fh_lam_h = lambda_home * 0.45
    fh_lam_a = lambda_away * 0.45
    fh_matrix = _compute_scoreline_matrix(fh_lam_h, fh_lam_a, max_goals=6)
    prob_fh_home = sum(p for (h, a), p in fh_matrix.items() if h > a)
    prob_fh_draw = sum(p for (h, a), p in fh_matrix.items() if h == a)
    prob_fh_away = sum(p for (h, a), p in fh_matrix.items() if h < a)

    return MatchPrediction(
        home_team=home_team,
        away_team=away_team,
        competition=competition,
        lambda_home=lambda_home,
        lambda_away=lambda_away,
        prob_home_win=prob_home_win,
        prob_draw=prob_draw,
        prob_away_win=prob_away_win,
        prob_over_1_5=prob_over_1_5,
        prob_over_2_5=prob_over_2_5,
        prob_over_3_5=prob_over_3_5,
        prob_over_4_5=prob_over_4_5,
        prob_btts_yes=prob_btts_yes,
        prob_home_spread_1_5=prob_home_spread_1_5,
        prob_home_spread_2_5=prob_home_spread_2_5,
        prob_away_spread_1_5=prob_away_spread_1_5,
        prob_away_spread_2_5=prob_away_spread_2_5,
        prob_first_half_home=prob_fh_home,
        prob_first_half_draw=prob_fh_draw,
        prob_first_half_away=prob_fh_away,
        home_team_matches=home_matches,
        away_team_matches=away_matches,
    )


# ---------------------------------------------------------------------------
# Competition code mapping  (football-data.org code → Kalshi competition string)
# ---------------------------------------------------------------------------

# Kalshi uses "EPL", "Bundesliga", "UCL" as competition identifiers.
# football-data.org uses "PL", "BL1", "CL".
_FD_TO_KALSHI_COMP: Dict[str, str] = {
    "PL":  "EPL",
    "BL1": "Bundesliga",
    "CL":  "UCL",
}
_KALSHI_TO_FD_COMP: Dict[str, str] = {v: k for k, v in _FD_TO_KALSHI_COMP.items()}


# ---------------------------------------------------------------------------
# Main model class
# ---------------------------------------------------------------------------

class CalibratedPoissonModel:
    """Dixon-Coles-inspired Poisson model calibrated on historical results.

    Calibration computes per-team attack/defence strengths relative to the
    league average.  At prediction time, the strength parameters are combined
    with the league averages to produce match-specific expected-goals values.

    lambda_home = avg_home_goals * home.attack_home * away.defense_away
    lambda_away = avg_away_goals * away.attack_away * home.defense_home
    """

    def __init__(self) -> None:
        # Keyed by competition code (Kalshi style: 'EPL', 'Bundesliga', 'UCL')
        self.league_stats: Dict[str, LeagueStats] = {}

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self, results: List[MatchResult]) -> None:
        """Calibrate team strengths from a list of historical match results.

        Groups results by competition, computes league averages, then
        derives per-team attack and defence ratings relative to those averages.

        Args:
            results: List of MatchResult objects (typically from
                     ``load_historical_results()``).
        """
        # Group by competition
        by_comp: Dict[str, List[MatchResult]] = defaultdict(list)
        for r in results:
            # Normalise competition key to Kalshi style
            comp_key = _FD_TO_KALSHI_COMP.get(r.competition, r.competition)
            by_comp[comp_key].append(r)

        for comp, comp_results in by_comp.items():
            self.league_stats[comp] = self._calibrate_competition(comp_results)
            logger.info(
                "calibrated: %s → %d matches, %d teams",
                comp, len(comp_results), len(self.league_stats[comp].team_strengths),
            )

    def _calibrate_competition(self, results: List[MatchResult]) -> LeagueStats:
        """Compute LeagueStats for a single competition from its results.

        Uses exponential-decay recency weighting so that recent matches count
        more than older ones.  Half-life is 60 days: a match played 60 days ago
        contributes half as much as one played today.
        """
        if not results:
            return LeagueStats(avg_home_goals=1.5, avg_away_goals=1.2, team_strengths={})

        # ── Recency weight helper ────────────────────────────────────────
        _HALF_LIFE_DAYS: float = 60.0
        _DECAY: float = math.log(2) / _HALF_LIFE_DAYS  # = 0.693 / 60
        now = datetime.now(tz=timezone.utc)

        def _weight(match_date: Optional[datetime]) -> float:
            if match_date is None:
                return 1.0
            # Ensure timezone-aware
            if match_date.tzinfo is None:
                match_date = match_date.replace(tzinfo=timezone.utc)
            days_old = max(0.0, (now - match_date).total_seconds() / 86400.0)
            return math.exp(-_DECAY * days_old)

        # ── League-wide weighted averages ────────────────────────────────
        total_home_w = 0.0
        total_away_w = 0.0
        total_w = 0.0
        for r in results:
            w = _weight(r.date)
            total_home_w += w * r.home_goals
            total_away_w += w * r.away_goals
            total_w += w

        avg_home_goals = total_home_w / total_w if total_w > 0 else 1.5
        avg_away_goals = total_away_w / total_w if total_w > 0 else 1.2

        # ── Per-team weighted accumulators ───────────────────────────────
        # (weighted_goal_sum, total_weight) per team per context
        hs_wsum:  Dict[str, float] = defaultdict(float)   # home scored
        hs_wtot:  Dict[str, float] = defaultdict(float)
        hc_wsum:  Dict[str, float] = defaultdict(float)   # home conceded
        hc_wtot:  Dict[str, float] = defaultdict(float)
        as_wsum:  Dict[str, float] = defaultdict(float)   # away scored
        as_wtot:  Dict[str, float] = defaultdict(float)
        ac_wsum:  Dict[str, float] = defaultdict(float)   # away conceded
        ac_wtot:  Dict[str, float] = defaultdict(float)
        home_cnt: Dict[str, int]   = defaultdict(int)
        away_cnt: Dict[str, int]   = defaultdict(int)

        for r in results:
            w = _weight(r.date)
            ht = normalise_team_name(r.home_team)
            at = normalise_team_name(r.away_team)

            hs_wsum[ht]  += w * r.home_goals
            hs_wtot[ht]  += w
            hc_wsum[ht]  += w * r.away_goals
            hc_wtot[ht]  += w
            as_wsum[at]  += w * r.away_goals
            as_wtot[at]  += w
            ac_wsum[at]  += w * r.home_goals
            ac_wtot[at]  += w
            home_cnt[ht] += 1
            away_cnt[at] += 1

        # ── Build team strengths ─────────────────────────────────────────
        all_teams = set(hs_wsum) | set(as_wsum)
        team_strengths: Dict[str, TeamStrength] = {}

        for team in all_teams:
            # Weighted average goals scored at home
            hs_avg = hs_wsum[team] / hs_wtot[team] if hs_wtot.get(team, 0) > 0 else avg_home_goals
            # Weighted average goals scored away
            as_avg = as_wsum[team] / as_wtot[team] if as_wtot.get(team, 0) > 0 else avg_away_goals
            # Weighted average goals conceded at home (away team scoring)
            hc_avg = hc_wsum[team] / hc_wtot[team] if hc_wtot.get(team, 0) > 0 else avg_away_goals
            # Weighted average goals conceded away
            ac_avg = ac_wsum[team] / ac_wtot[team] if ac_wtot.get(team, 0) > 0 else avg_home_goals

            attack_home  = hs_avg / avg_home_goals if avg_home_goals > 0 else 1.0
            attack_away  = as_avg / avg_away_goals if avg_away_goals > 0 else 1.0
            defense_home = hc_avg / avg_away_goals if avg_away_goals > 0 else 1.0
            defense_away = ac_avg / avg_home_goals if avg_home_goals > 0 else 1.0

            matches_played = home_cnt[team] + away_cnt[team]

            team_strengths[team] = TeamStrength(
                attack_home=max(0.1, attack_home),
                attack_away=max(0.1, attack_away),
                defense_home=max(0.1, defense_home),
                defense_away=max(0.1, defense_away),
                matches_played=matches_played,
            )

        return LeagueStats(
            avg_home_goals=avg_home_goals,
            avg_away_goals=avg_away_goals,
            team_strengths=team_strengths,
        )

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_match(
        self,
        home_team: str,
        away_team: str,
        competition: str,
    ) -> MatchPrediction:
        """Generate full probability predictions for a match.

        Args:
            home_team: Team name (any known alias or canonical form).
            away_team: Team name (any known alias or canonical form).
            competition: Competition code — either Kalshi style ('EPL',
                         'Bundesliga', 'UCL') or football-data.org style
                         ('PL', 'BL1', 'CL').  Both are handled.

        Returns:
            MatchPrediction with lambdas and all market probabilities.

        Note:
            If a team has no historical data, its strength defaults to 1.0
            (league average), which gives a conservative prediction.
        """
        # Normalise competition to Kalshi style for league_stats lookup
        comp_key = _FD_TO_KALSHI_COMP.get(competition, competition)

        # Normalise team names
        home_norm = normalise_team_name(home_team)
        away_norm = normalise_team_name(away_team)

        # Get league stats (fall back to generic defaults if not calibrated yet)
        league = self.league_stats.get(comp_key)
        if league is None:
            logger.warning(
                "predict_match: no calibration data for competition '%s', using defaults",
                comp_key,
            )
            league = LeagueStats(
                avg_home_goals=1.5,
                avg_away_goals=1.2,
                team_strengths={},
            )

        # Look up team strengths (fall back to 1.0 = league average)
        _DEFAULT_STRENGTH = TeamStrength(
            attack_home=1.0, attack_away=1.0,
            defense_home=1.0, defense_away=1.0,
            matches_played=0,
        )
        home_str = league.team_strengths.get(home_norm, _DEFAULT_STRENGTH)
        away_str = league.team_strengths.get(away_norm, _DEFAULT_STRENGTH)

        # Dixon-Coles style lambda computation
        lambda_home = (
            league.avg_home_goals
            * home_str.attack_home
            * away_str.defense_away
        )
        lambda_away = (
            league.avg_away_goals
            * away_str.attack_away
            * home_str.defense_home
        )

        # Guard against degenerate values
        lambda_home = max(0.1, lambda_home)
        lambda_away = max(0.1, lambda_away)

        return _derive_probabilities(
            lambda_home=lambda_home,
            lambda_away=lambda_away,
            home_team=home_norm,
            away_team=away_norm,
            competition=comp_key,
            home_matches=home_str.matches_played,
            away_matches=away_str.matches_played,
        )

    def predict_from_kalshi_match(self, match: SoccerMatch) -> MatchPrediction:
        """Generate a prediction directly from a KalshiSoccerClient SoccerMatch.

        Handles fuzzy team name resolution between Kalshi and football-data.org
        naming conventions automatically.

        Args:
            match: SoccerMatch from KalshiSoccerClient.fetch_match_markets().

        Returns:
            MatchPrediction for the match.
        """
        return self.predict_match(
            home_team=match.home_team,
            away_team=match.away_team,
            competition=match.competition,
        )

    # ------------------------------------------------------------------
    # Convenience: calibrate-and-predict from raw team names
    # ------------------------------------------------------------------

    def is_calibrated(self, competition: Optional[str] = None) -> bool:
        """Return True if the model has been calibrated (for the given competition)."""
        if competition:
            comp_key = _FD_TO_KALSHI_COMP.get(competition, competition)
            return comp_key in self.league_stats
        return bool(self.league_stats)

    def known_teams(self, competition: Optional[str] = None) -> List[str]:
        """List all teams the model has been calibrated on."""
        if competition:
            comp_key = _FD_TO_KALSHI_COMP.get(competition, competition)
            league = self.league_stats.get(comp_key)
            return list(league.team_strengths.keys()) if league else []
        teams = []
        for league in self.league_stats.values():
            teams.extend(league.team_strengths.keys())
        return teams

    def team_strength(self, team_name: str, competition: str) -> Optional[TeamStrength]:
        """Return the TeamStrength for a team, or None if not calibrated."""
        comp_key = _FD_TO_KALSHI_COMP.get(competition, competition)
        league = self.league_stats.get(comp_key)
        if not league:
            return None
        norm = normalise_team_name(team_name)
        return league.team_strengths.get(norm)


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

def _run_cli() -> None:
    """Fetch data, calibrate, generate signals, and print a summary table."""
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    print("=" * 70)
    print("  Football Intel — Calibrated Poisson Signal Runner")
    print("=" * 70)

    # ── Step 1: Load historical data ────────────────────────────────────
    print("\n[1/5] Loading historical match data…", flush=True)
    try:
        results = load_historical_results()
        print(f"      {len(results)} historical results loaded")
    except Exception as exc:
        print(f"      ERROR: {exc}")
        sys.exit(1)

    # ── Step 2: Calibrate the model ──────────────────────────────────────
    print("\n[2/5] Calibrating model…", flush=True)
    model = CalibratedPoissonModel()
    model.calibrate(results)
    for comp, stats in model.league_stats.items():
        print(
            f"      {comp}: {len(stats.team_strengths)} teams, "
            f"avg_home={stats.avg_home_goals:.2f}, avg_away={stats.avg_away_goals:.2f}"
        )

    # ── Step 3: Fetch Kalshi markets ─────────────────────────────────────
    print("\n[3/5] Fetching Kalshi soccer markets…", flush=True)
    try:
        from football_intel.ingestion.kalshi_soccer import KalshiSoccerClient
        ks_client = KalshiSoccerClient()
        matches = ks_client.fetch_match_markets()
        print(f"      {len(matches)} matches found on Kalshi")
    except Exception as exc:
        print(f"      ERROR fetching Kalshi data: {exc}")
        sys.exit(1)

    if not matches:
        print("\nNo upcoming matches found on Kalshi. Exiting.")
        sys.exit(0)

    # ── Step 4: Generate signals ─────────────────────────────────────────
    print("\n[4/5] Generating betting signals…", flush=True)
    from football_intel.strategy.signal_generator import SignalGenerator
    generator = SignalGenerator(model)
    signals = generator.generate_signals(matches, min_edge=0.05)
    print(f"      {len(signals)} signals with edge ≥ 5%")

    # ── Step 5: Print results ────────────────────────────────────────────
    print("\n[5/5] Top signals sorted by EV per dollar\n")

    if not signals:
        print("  No positive-edge signals found today.")
        return

    # Header
    col_widths = [28, 12, 14, 8, 8, 8, 8, 10, 7]
    header = (
        f"{'Match':<28} {'Comp':<12} {'Bet':<14} "
        f"{'Model%':>8} {'Kalshi%':>8} {'Edge':>8} {'EV/$':>8} "
        f"{'Conf':<10} {'Ticker'}"
    )
    print(header)
    print("-" * 120)

    signals_sorted = sorted(signals, key=lambda s: s.ev_per_dollar, reverse=True)
    for s in signals_sorted[:30]:  # show top 30
        print(
            f"{s.match_title:<28} {s.competition:<12} {s.bet_type:<14} "
            f"{s.model_prob:>7.1%} {s.kalshi_implied_prob:>8.1%} "
            f"{s.edge:>8.3f} {s.ev_per_dollar:>8.4f} "
            f"{s.confidence:<10} {s.market_ticker}"
        )
        print(f"  └─ {s.description}")

    print(f"\n  Total signals: {len(signals)}")


if __name__ == "__main__":
    _run_cli()
