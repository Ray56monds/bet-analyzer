"""
Core Analyzer — dispatches to sport-specific engines and filters
results by the 70% minimum probability threshold.
"""
from models import Game, Sport, BetType, BetAnalysis
from sports import football, basketball, tennis

MIN_PROBABILITY = 0.70  # Only recommend bets with >= 70% calculated win probability


def analyze_game(game: Game) -> list[BetAnalysis]:
    """
    Run all three bet-type analyses for a game.
    Returns ALL results (including below threshold) so callers can inspect.
    """
    if game.sport == Sport.FOOTBALL:
        engine = football
    elif game.sport == Sport.BASKETBALL:
        engine = basketball
    elif game.sport == Sport.TENNIS:
        engine = tennis
    else:
        raise ValueError(f"Unsupported sport: {game.sport}")

    results: list[BetAnalysis] = []

    try:
        results.append(engine.analyze_ft_over(game))
    except Exception as e:
        print(f"[WARN] FT Over analysis failed for {game.id}: {e}")

    try:
        results.append(engine.analyze_ht_over(game))
    except Exception as e:
        print(f"[WARN] HT Over analysis failed for {game.id}: {e}")

    try:
        results.append(engine.analyze_handicap(game))
    except Exception as e:
        print(f"[WARN] Handicap analysis failed for {game.id}: {e}")

    return results


def filter_recommended(analyses: list[BetAnalysis],
                        min_prob: float = MIN_PROBABILITY) -> list[BetAnalysis]:
    """Filter to only recommended bets above probability threshold."""
    return [a for a in analyses if a.probability >= min_prob and a.expected_value > 0]


def analyze_all_games(games: list[Game],
                      min_prob: float = MIN_PROBABILITY) -> dict[str, list[BetAnalysis]]:
    """
    Analyze a list of games.
    Returns a dict: game_id -> list of recommended BetAnalysis.
    Only games with at least one qualifying bet are included.
    """
    results: dict[str, list[BetAnalysis]] = {}

    for game in games:
        all_analyses = analyze_game(game)
        recommended = filter_recommended(all_analyses, min_prob)
        if recommended:
            results[game.id] = recommended

    return results


def rank_analyses(analyses: list[BetAnalysis]) -> list[BetAnalysis]:
    """Sort by expected value descending, then probability descending."""
    return sorted(analyses, key=lambda a: (a.expected_value, a.probability), reverse=True)
