"""
Tennis-specific analysis engine.

Tennis doesn't have a traditional "halftime" so:
- Full Time Over = Total games in match over X (e.g. Over 21.5)
- Half Time Over = First set total games over X (e.g. Over 10.5 in set 1)
- Handicap = Set handicap (e.g. favorite -1.5 sets)

Surface: 'hard', 'clay', 'grass'
"""
import math
from models import Game, BetType, BetAnalysis


def _normal_prob_over(mean: float, std: float, threshold: float) -> float:
    z = (threshold - mean) / max(std, 0.1)
    return max(0.05, min(0.95, 0.5 * math.erfc(z / math.sqrt(2))))


# Tennis games distribution std deviations
MATCH_GAMES_STD = 4.5
SET_GAMES_STD = 2.0
SET_HANDICAP_STD = 0.8


# Surface modifiers for avg games per set (baseline ~10 games per set)
SURFACE_GAMES = {
    "clay": 11.2,   # longer rallies, more games
    "hard": 10.5,
    "grass": 9.8,   # faster surface, quicker points
    None: 10.5,
}

SURFACE_BREAK_RATE = {
    "clay": 0.30,   # more breaks on clay
    "hard": 0.22,
    "grass": 0.18,  # fewer breaks on grass
    None: 0.22,
}


def _surface_avg_games(surface: str | None) -> float:
    return SURFACE_GAMES.get(surface, 10.5)


def _surface_break_rate(surface: str | None) -> float:
    return SURFACE_BREAK_RATE.get(surface, 0.22)


def _expected_match_games(home_avg: float, away_avg: float, surface: str | None,
                           num_sets: float = 3.0) -> float:
    """Estimate total games in match."""
    surface_base = _surface_avg_games(surface)
    per_set_games = (home_avg + away_avg) / 2.0
    # Weight surface factor
    per_set_games = per_set_games * 0.7 + surface_base * 0.3
    return per_set_games * num_sets


def analyze_ft_over(game: Game) -> BetAnalysis:
    """Analyze Full Time Over total games."""
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # Average games per set each player plays (use avg_scored as avg games/set won)
    # avg_scored here represents avg games won per set
    home_games_per_set = home.avg_scored + home.avg_conceded  # total games in sets they play
    away_games_per_set = away.avg_scored + away.avg_conceded
    avg_games_per_set = (home_games_per_set + away_games_per_set) / 2

    # Expected sets: best of 3 on tour typically goes ~2.4 sets on average
    # Rank difference affects set count (close matches = more sets)
    rank_gap = abs(home.rank - away.rank)
    if rank_gap < 20:
        expected_sets = 2.6  # competitive
    elif rank_gap < 50:
        expected_sets = 2.4
    else:
        expected_sets = 2.1  # mismatch, fewer sets

    total_xg = avg_games_per_set * expected_sets

    # H2H adjustment
    if h2h.total_games > 0:
        total_xg = total_xg * 0.75 + h2h.avg_total_goals * 0.25

    # Surface modifier
    surface_mod = (_surface_avg_games(game.surface) - 10.5) * expected_sets * 0.15
    total_xg += surface_mod

    base_prob = _normal_prob_over(total_xg, MATCH_GAMES_STD, game.ft_over_line)

    ev = round((base_prob * game.ft_over_odds) - 1, 4)

    reasoning = [
        f"Avg games/set: {avg_games_per_set:.1f} | Expected sets: {expected_sets:.1f}",
        f"Total match xGames: {total_xg:.1f} | Surface: {game.surface or 'Unknown'}",
        f"Surface modifier: {surface_mod:+.1f}",
        f"H2H avg total games: {h2h.avg_total_goals:.1f}",
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
    """Analyze First Set Over total games."""
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # First set total games
    home_set1_games = home.ht_avg_scored + home.ht_avg_conceded
    away_set1_games = away.ht_avg_scored + away.ht_avg_conceded
    avg_set1_games = (home_set1_games + away_set1_games) / 2

    # Surface effect on set 1
    surface_base = _surface_avg_games(game.surface)
    avg_set1_games = avg_set1_games * 0.65 + surface_base * 0.35

    # H2H first set
    if h2h.total_games > 0:
        avg_set1_games = avg_set1_games * 0.75 + h2h.avg_ht_goals * 0.25

    base_prob = _normal_prob_over(avg_set1_games, SET_GAMES_STD, game.ht_over_line)

    ev = round((base_prob * game.ht_over_odds) - 1, 4)

    reasoning = [
        f"Avg set 1 games: {avg_set1_games:.1f} (incl. surface weight)",
        f"Surface: {game.surface or 'Unknown'} | Surface base: {surface_base:.1f}",
        f"H2H avg set 1 games: {h2h.avg_ht_goals:.1f}",
        f"Line: Set 1 Over {game.ht_over_line} | Odds: {game.ht_over_odds}",
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
    Analyze Set Handicap.
    handicap_line = -1.5 means favorite must win 2-0 (wins sets with 1.5 set margin).
    """
    home = game.home_team
    away = game.away_team
    h2h = game.h2h

    # Win probability based on ranking (Elo-style estimate)
    rank_diff = away.rank - home.rank  # positive = home is better ranked
    form_diff = home.form_score - away.form_score

    # Surface preference bonus (using avg_scored as surface win rate proxy)
    # Higher form on current surface = advantage
    net_advantage = rank_diff / 30.0 + form_diff * 0.4

    # H2H
    if h2h.total_games > 0:
        h2h_rate = h2h.home_wins / h2h.total_games
        net_advantage = net_advantage * 0.70 + (h2h_rate - 0.5) * 0.30

    # Base probability home wins match
    base_win_prob = 1.0 / (1.0 + math.exp(-2.0 * net_advantage))

    # Handicap adjustment: -1.5 sets means must win 2-0
    # P(win 2-0) = P(win)^2 approximately for independent sets
    # +1.5 means underdog only needs 1 set: P(win >= 1 set)
    line = game.handicap_line
    if line <= -1.5:
        # Need to win 2-0 (clean sweep)
        prob = base_win_prob ** 2.0
    elif line <= -0.5:
        # Standard win (covers -0.5)
        prob = base_win_prob
    elif line >= 1.5:
        # Underdog covers if wins at least 1 set
        prob = 1.0 - (1.0 - base_win_prob) ** 2.0
    else:
        prob = base_win_prob

    prob = max(0.05, min(0.95, prob))
    ev = round((prob * game.handicap_home_odds) - 1, 4)

    reasoning = [
        f"Rank diff: {rank_diff} (positive = home stronger)",
        f"Form diff: {form_diff:+.2f} | Net advantage: {net_advantage:+.2f}",
        f"Base match win prob: {base_win_prob:.1%}",
        f"Set handicap: {line:+.1f} | Adj. prob: {prob:.1%}",
        f"H2H: {h2h.home_wins}W / {h2h.total_games} games",
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
