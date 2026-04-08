"""
Football-specific analysis engine.

Models:
- Full Time Over (e.g. Over 2.5 goals)
- Half Time Over (e.g. Over 1.5 goals in first half)
- Handicap (home team -1, -1.5, etc.)
"""
from models import Game, BetType, BetAnalysis


def _poisson_prob_over(lam: float, threshold: float) -> float:
    """
    Approximate probability that a Poisson-distributed event count exceeds `threshold`.
    Uses cumulative Poisson CDF.
    """
    import math
    k = int(threshold)  # over threshold means at least k+1 goals
    target = k + 1
    # P(X >= target) = 1 - P(X <= k)
    cumulative = 0.0
    for i in range(target):
        cumulative += (lam ** i * math.exp(-lam)) / math.factorial(i)
    return max(0.0, min(1.0, 1.0 - cumulative))


def analyze_ft_over(game: Game) -> BetAnalysis:
    """Analyze Full Time Over probability."""
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # Expected goals using attack/defense blend
    home_attack = (home.avg_scored + away.avg_conceded) / 2
    away_attack = (away.avg_scored + home.avg_conceded) / 2

    # Home advantage boost (~0.3 extra goals at home)
    if game.is_home_match:
        home_xg = (home.home_avg_scored + away.away_avg_conceded) / 2 + 0.15
        away_xg = (away.away_avg_scored + home.home_avg_conceded) / 2 - 0.10
    else:
        home_xg = home_attack
        away_xg = away_attack

    total_xg = max(0.1, home_xg + away_xg)

    # H2H adjustment: weight 20%
    if h2h.total_games > 0:
        total_xg = total_xg * 0.80 + h2h.avg_total_goals * 0.20

    # Form factor: high-scoring form increases expectation slightly
    form_boost = ((home.form_score + away.form_score) / 2 - 0.5) * 0.2
    total_xg += form_boost

    base_prob = _poisson_prob_over(total_xg, game.ft_over_line)

    ev = round((base_prob * game.ft_over_odds) - 1, 4)

    reasoning = [
        f"Home xG: {home_xg:.2f} | Away xG: {away_xg:.2f} | Total xG: {total_xg:.2f}",
        f"H2H avg total goals: {h2h.avg_total_goals:.2f} over {h2h.total_games} games",
        f"Home form score: {home.form_score:.0%} | Away form score: {away.form_score:.0%}",
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
    """Analyze Half Time Over probability."""
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # First half typically sees ~40-45% of match goals
    ht_ratio = 0.42

    if game.is_home_match:
        home_ht_xg = (home.ht_avg_scored + away.ht_avg_conceded) / 2
        away_ht_xg = (away.ht_avg_scored + home.ht_avg_conceded) / 2
    else:
        home_ht_xg = home.ht_avg_scored
        away_ht_xg = away.ht_avg_scored

    total_ht_xg = max(0.1, home_ht_xg + away_ht_xg)

    # H2H first-half adjustment
    if h2h.total_games > 0:
        total_ht_xg = total_ht_xg * 0.75 + h2h.avg_ht_goals * 0.25

    base_prob = _poisson_prob_over(total_ht_xg, game.ht_over_line)

    ev = round((base_prob * game.ht_over_odds) - 1, 4)

    reasoning = [
        f"Home HT xG: {home_ht_xg:.2f} | Away HT xG: {away_ht_xg:.2f}",
        f"Total HT xG: {total_ht_xg:.2f}",
        f"H2H avg HT goals: {h2h.avg_ht_goals:.2f}",
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
    """
    Analyze Handicap bet (home team handicap).
    Positive handicap_line means home is given extra goals (underdog).
    Negative means home must win by that margin.
    """
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # Expected goal difference
    if game.is_home_match:
        home_xg = (home.home_avg_scored + away.away_avg_conceded) / 2 + 0.25
        away_xg = (away.away_avg_scored + home.home_avg_conceded) / 2
    else:
        home_xg = home.avg_scored
        away_xg = away.avg_scored

    xg_diff = home_xg - away_xg  # positive = home favored

    # Form difference
    form_diff = home.form_score - away.form_score

    # Rank difference (lower rank = stronger team; normalize by 50)
    rank_diff = (away.rank - home.rank) / 50.0

    # Combine: xg_diff is primary, form and rank are modifiers
    net_strength = xg_diff + (form_diff * 0.3) + (rank_diff * 0.2)

    # H2H home win rate
    if h2h.total_games > 0:
        h2h_home_rate = h2h.home_wins / h2h.total_games
        net_strength = net_strength * 0.75 + (h2h_home_rate - 0.5) * 0.25

    # Convert net_strength to probability using sigmoid-like curve
    # handicap_line: e.g. -1.5 means we need home to win by 2+
    # Adjust net_strength by handicap line
    adjusted = net_strength + game.handicap_line  # line is negative for home fav
    # Map to probability (sigmoid centered at 0)
    import math
    prob = 1.0 / (1.0 + math.exp(-2.5 * adjusted))
    prob = max(0.05, min(0.95, prob))

    ev = round((prob * game.handicap_home_odds) - 1, 4)

    reasoning = [
        f"Home xG: {home_xg:.2f} | Away xG: {away_xg:.2f} | xG diff: {xg_diff:+.2f}",
        f"Form diff: {form_diff:+.2f} | Rank diff factor: {rank_diff:+.2f}",
        f"Net strength: {net_strength:+.2f} | Handicap line: {game.handicap_line:+.1f}",
        f"H2H home wins: {h2h.home_wins}/{h2h.total_games}",
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
