"""
Basketball-specific analysis engine.

Models:
- Full Time Over (total points, e.g. Over 215.5)
- Half Time Over (first half total, e.g. Over 105.5)
- Handicap (point spread, e.g. home -5.5)
"""
import math
from models import Game, BetType, BetAnalysis


def _normal_prob_over(mean: float, std: float, threshold: float) -> float:
    """
    P(X > threshold) for a Normal distribution with given mean and std.
    Uses complementary error function approximation.
    """
    z = (threshold - mean) / max(std, 0.1)
    # erfc approximation
    prob = 0.5 * math.erfc(z / math.sqrt(2))
    return max(0.05, min(0.95, prob))


# Basketball total points standard deviation (typical for NBA-style games)
FT_STD = 12.0
HT_STD = 7.0
SPREAD_STD = 10.0


def analyze_ft_over(game: Game) -> BetAnalysis:
    """Analyze Full Time Over for basketball."""
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # Expected total points
    if game.is_home_match:
        home_pts = (home.home_avg_scored + away.away_avg_conceded) / 2
        away_pts = (away.away_avg_scored + home.home_avg_conceded) / 2
    else:
        home_pts = (home.avg_scored + away.avg_conceded) / 2
        away_pts = (away.avg_scored + home.avg_conceded) / 2

    total_xp = home_pts + away_pts

    # H2H adjustment
    if h2h.total_games > 0:
        total_xp = total_xp * 0.80 + h2h.avg_total_goals * 0.20

    # Form factor (high-scoring form = more points)
    form_factor = ((home.form_score + away.form_score) / 2 - 0.5) * 6.0
    total_xp += form_factor

    base_prob = _normal_prob_over(total_xp, FT_STD, game.ft_over_line)

    ev = round((base_prob * game.ft_over_odds) - 1, 4)

    reasoning = [
        f"Home xPTS: {home_pts:.1f} | Away xPTS: {away_pts:.1f} | Total xPTS: {total_xp:.1f}",
        f"H2H avg total pts: {h2h.avg_total_goals:.1f} over {h2h.total_games} games",
        f"Form boost: {form_factor:+.1f}",
        f"Line: Over {game.ft_over_line} | Odds: {game.ft_over_odds}",
        f"Expected Value: {ev:+.3f}",
    ]

    confidence = "HIGH" if base_prob >= 0.78 else ("MEDIUM" if base_prob >= 0.70 else "LOW")

    return BetAnalysis(
        game=game,
        bet_type=BetType.FULLTIME_OVER,
        line=game.ft_over_line,
        odds=game.ft_over_odds,
        probability=round(base_prob, 4),
        confidence=confidence,
        expected_value=ev,
        reasoning=reasoning,
    )


def analyze_ht_over(game: Game) -> BetAnalysis:
    """Analyze Half Time Over for basketball (first two quarters)."""
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # First half is roughly 47-50% of total points
    ht_ratio = 0.48

    home_ht = (home.ht_avg_scored + away.ht_avg_conceded) / 2
    away_ht = (away.ht_avg_scored + home.ht_avg_conceded) / 2
    total_ht_xp = home_ht + away_ht

    if h2h.total_games > 0:
        total_ht_xp = total_ht_xp * 0.75 + h2h.avg_ht_goals * 0.25

    base_prob = _normal_prob_over(total_ht_xp, HT_STD, game.ht_over_line)

    ev = round((base_prob * game.ht_over_odds) - 1, 4)

    reasoning = [
        f"Home HT xPTS: {home_ht:.1f} | Away HT xPTS: {away_ht:.1f}",
        f"Total HT xPTS: {total_ht_xp:.1f}",
        f"H2H avg HT pts: {h2h.avg_ht_goals:.1f}",
        f"Line: HT Over {game.ht_over_line} | Odds: {game.ht_over_odds}",
        f"Expected Value: {ev:+.3f}",
    ]

    confidence = "HIGH" if base_prob >= 0.78 else ("MEDIUM" if base_prob >= 0.70 else "LOW")

    return BetAnalysis(
        game=game,
        bet_type=BetType.HALFTIME_OVER,
        line=game.ht_over_line,
        odds=game.ht_over_odds,
        probability=round(base_prob, 4),
        confidence=confidence,
        expected_value=ev,
        reasoning=reasoning,
    )


def analyze_handicap(game: Game) -> BetAnalysis:
    """Analyze Handicap (point spread) for basketball."""
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # Expected scoring difference
    if game.is_home_match:
        home_xp = (home.home_avg_scored + away.away_avg_conceded) / 2 + 3.0  # home court +3
        away_xp = (away.away_avg_scored + home.home_avg_conceded) / 2
    else:
        home_xp = (home.avg_scored + away.avg_conceded) / 2
        away_xp = (away.avg_scored + home.avg_conceded) / 2

    xp_diff = home_xp - away_xp  # positive = home favored

    # Form and rank modifiers
    form_mod = (home.form_score - away.form_score) * 5.0
    rank_mod = (away.rank - home.rank) / 10.0

    net_margin = xp_diff + form_mod + rank_mod

    # H2H
    if h2h.total_games > 0:
        h2h_margin = (h2h.home_wins - h2h.away_wins) / h2h.total_games * 5.0
        net_margin = net_margin * 0.80 + h2h_margin * 0.20

    # With handicap applied, does home still cover?
    adjusted_margin = net_margin + game.handicap_line  # negative line = home gives points

    prob = _normal_prob_over(adjusted_margin, SPREAD_STD, 0.5)

    ev = round((prob * game.handicap_home_odds) - 1, 4)

    reasoning = [
        f"Home xPTS: {home_xp:.1f} | Away xPTS: {away_xp:.1f} | Margin: {xp_diff:+.1f}",
        f"Form mod: {form_mod:+.1f} | Rank mod: {rank_mod:+.1f}",
        f"Net margin: {net_margin:+.1f} | Handicap line: {game.handicap_line:+.1f}",
        f"H2H: {h2h.home_wins}W-{h2h.draws}D-{h2h.away_wins}L",
        f"Odds: {game.handicap_home_odds} | Expected Value: {ev:+.3f}",
    ]

    confidence = "HIGH" if prob >= 0.78 else ("MEDIUM" if prob >= 0.70 else "LOW")

    return BetAnalysis(
        game=game,
        bet_type=BetType.HANDICAP,
        line=game.handicap_line,
        odds=game.handicap_home_odds,
        probability=round(prob, 4),
        confidence=confidence,
        expected_value=ev,
        reasoning=reasoning,
    )
