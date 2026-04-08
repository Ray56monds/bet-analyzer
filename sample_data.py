"""
Sample game data for demonstration.
In a real integration, replace this with live data from a sports data API
(e.g. API-Football, TheSportsDB, BallDontLie, RapidAPI sports endpoints).

Each TeamStats field meaning per sport:
  Football:   avg_scored/conceded = goals/game; ht_avg = first-half goals/game
  Basketball: avg_scored/conceded = points/game; ht_avg = first-half points/game
  Tennis:     avg_scored = avg games WON per set; avg_conceded = avg games LOST per set
              ht_avg = set-1 games won/lost
"""
from models import Game, Sport, TeamStats, HeadToHead


# ── FOOTBALL GAMES ───────────────────────────────────────────────────────────

FOOTBALL_GAMES: list[Game] = [
    # Elite team vs relegation side — heavily one-sided, massive goal expectation
    Game(
        id="fb_005",
        sport=Sport.FOOTBALL,
        league="Champions League",
        home_team=TeamStats(
            name="Real Madrid",
            form=["W", "W", "W", "W", "W"],
            avg_scored=3.5, avg_conceded=0.7,
            home_avg_scored=4.0, home_avg_conceded=0.5,
            away_avg_scored=3.0, away_avg_conceded=0.9,
            rank=1,
            ht_avg_scored=1.9, ht_avg_conceded=0.3,
        ),
        away_team=TeamStats(
            name="Shakhtar Donetsk",
            form=["L", "D", "L", "L", "D"],
            avg_scored=1.1, avg_conceded=3.0,
            home_avg_scored=1.4, home_avg_conceded=2.6,
            away_avg_scored=0.8, away_avg_conceded=3.5,
            rank=25,
            ht_avg_scored=0.4, ht_avg_conceded=1.7,
        ),
        h2h=HeadToHead(total_games=6, home_wins=6, away_wins=0, draws=0,
                       avg_total_goals=5.0, avg_ht_goals=2.3),
        handicap_line=-2.5, handicap_home_odds=1.95, handicap_away_odds=1.95,
        ht_over_line=0.5,   ht_over_odds=1.55,
        ft_over_line=2.5,   ft_over_odds=1.80,
    ),
    # Eredivisie: Ajax vs bottom side — high Dutch football goal rates
    Game(
        id="fb_006",
        sport=Sport.FOOTBALL,
        league="Eredivisie",
        home_team=TeamStats(
            name="Ajax",
            form=["W", "W", "W", "W", "D"],
            avg_scored=4.0, avg_conceded=0.9,
            home_avg_scored=4.6, home_avg_conceded=0.7,
            away_avg_scored=3.4, away_avg_conceded=1.1,
            rank=1,
            ht_avg_scored=2.1, ht_avg_conceded=0.4,
        ),
        away_team=TeamStats(
            name="Excelsior",
            form=["L", "L", "L", "D", "L"],
            avg_scored=0.9, avg_conceded=3.3,
            home_avg_scored=1.1, home_avg_conceded=3.0,
            away_avg_scored=0.7, away_avg_conceded=3.7,
            rank=16,
            ht_avg_scored=0.3, ht_avg_conceded=1.8,
        ),
        h2h=HeadToHead(total_games=8, home_wins=8, away_wins=0, draws=0,
                       avg_total_goals=5.5, avg_ht_goals=2.4),
        handicap_line=-2.5, handicap_home_odds=1.90, handicap_away_odds=2.00,
        ht_over_line=0.5,   ht_over_odds=1.55,
        ft_over_line=2.5,   ft_over_odds=1.75,
    ),
    Game(
        id="fb_001",
        sport=Sport.FOOTBALL,
        league="Premier League",
        home_team=TeamStats(
            name="Manchester City",
            form=["W", "W", "W", "D", "W"],
            avg_scored=2.8, avg_conceded=0.8,
            home_avg_scored=3.1, home_avg_conceded=0.6,
            away_avg_scored=2.4, away_avg_conceded=1.0,
            rank=1,
            ht_avg_scored=1.3, ht_avg_conceded=0.4,
        ),
        away_team=TeamStats(
            name="Brentford",
            form=["L", "W", "L", "D", "L"],
            avg_scored=1.3, avg_conceded=1.8,
            home_avg_scored=1.5, home_avg_conceded=1.6,
            away_avg_scored=1.1, away_avg_conceded=2.1,
            rank=14,
            ht_avg_scored=0.5, ht_avg_conceded=0.9,
        ),
        h2h=HeadToHead(total_games=10, home_wins=8, away_wins=1, draws=1,
                       avg_total_goals=3.6, avg_ht_goals=1.6),
        handicap_line=-1.5, handicap_home_odds=1.80, handicap_away_odds=2.10,
        ht_over_line=1.5,   ht_over_odds=1.95,
        ft_over_line=2.5,   ft_over_odds=1.75,
    ),
    Game(
        id="fb_002",
        sport=Sport.FOOTBALL,
        league="La Liga",
        home_team=TeamStats(
            name="Barcelona",
            form=["W", "W", "D", "W", "W"],
            avg_scored=2.6, avg_conceded=0.9,
            home_avg_scored=2.9, home_avg_conceded=0.7,
            away_avg_scored=2.2, away_avg_conceded=1.1,
            rank=2,
            ht_avg_scored=1.2, ht_avg_conceded=0.4,
        ),
        away_team=TeamStats(
            name="Getafe",
            form=["D", "L", "D", "L", "W"],
            avg_scored=1.1, avg_conceded=1.5,
            home_avg_scored=1.4, home_avg_conceded=1.3,
            away_avg_scored=0.9, away_avg_conceded=1.8,
            rank=15,
            ht_avg_scored=0.5, ht_avg_conceded=0.8,
        ),
        h2h=HeadToHead(total_games=8, home_wins=6, away_wins=1, draws=1,
                       avg_total_goals=3.1, avg_ht_goals=1.4),
        handicap_line=-1.5, handicap_home_odds=1.85, handicap_away_odds=2.05,
        ht_over_line=1.5,   ht_over_odds=2.00,
        ft_over_line=2.5,   ft_over_odds=1.70,
    ),
    Game(
        id="fb_003",
        sport=Sport.FOOTBALL,
        league="Bundesliga",
        home_team=TeamStats(
            name="Leverkusen",
            form=["W", "D", "W", "W", "W"],
            avg_scored=2.4, avg_conceded=1.0,
            home_avg_scored=2.7, home_avg_conceded=0.9,
            away_avg_scored=2.1, away_avg_conceded=1.2,
            rank=3,
            ht_avg_scored=1.1, ht_avg_conceded=0.5,
        ),
        away_team=TeamStats(
            name="Hoffenheim",
            form=["L", "D", "W", "L", "D"],
            avg_scored=1.5, avg_conceded=1.7,
            home_avg_scored=1.7, home_avg_conceded=1.5,
            away_avg_scored=1.3, away_avg_conceded=2.0,
            rank=10,
            ht_avg_scored=0.7, ht_avg_conceded=0.9,
        ),
        h2h=HeadToHead(total_games=6, home_wins=4, away_wins=1, draws=1,
                       avg_total_goals=3.3, avg_ht_goals=1.5),
        handicap_line=-1.5, handicap_home_odds=1.90, handicap_away_odds=2.00,
        ht_over_line=1.5,   ht_over_odds=2.05,
        ft_over_line=2.5,   ft_over_odds=1.72,
    ),
    Game(
        id="fb_004",
        sport=Sport.FOOTBALL,
        league="Serie A",
        home_team=TeamStats(
            name="Napoli",
            form=["W", "W", "L", "W", "D"],
            avg_scored=2.0, avg_conceded=1.1,
            home_avg_scored=2.3, home_avg_conceded=0.9,
            away_avg_scored=1.7, away_avg_conceded=1.3,
            rank=4,
            ht_avg_scored=0.9, ht_avg_conceded=0.5,
        ),
        away_team=TeamStats(
            name="Salernitana",
            form=["L", "L", "D", "L", "L"],
            avg_scored=0.9, avg_conceded=2.1,
            home_avg_scored=1.1, home_avg_conceded=1.9,
            away_avg_scored=0.7, away_avg_conceded=2.4,
            rank=18,
            ht_avg_scored=0.4, ht_avg_conceded=1.1,
        ),
        h2h=HeadToHead(total_games=6, home_wins=5, away_wins=0, draws=1,
                       avg_total_goals=3.0, avg_ht_goals=1.3),
        handicap_line=-1.5, handicap_home_odds=1.75, handicap_away_odds=2.20,
        ht_over_line=1.5,   ht_over_odds=2.10,
        ft_over_line=2.5,   ft_over_odds=1.68,
    ),
]


# ── BASKETBALL GAMES ─────────────────────────────────────────────────────────

BASKETBALL_GAMES: list[Game] = [
    Game(
        id="bb_001",
        sport=Sport.BASKETBALL,
        league="NBA",
        home_team=TeamStats(
            name="Boston Celtics",
            form=["W", "W", "W", "L", "W"],
            avg_scored=118.5, avg_conceded=108.0,
            home_avg_scored=121.0, home_avg_conceded=106.0,
            away_avg_scored=115.5, away_avg_conceded=110.5,
            rank=1,
            ht_avg_scored=59.2, ht_avg_conceded=53.5,
        ),
        away_team=TeamStats(
            name="Washington Wizards",
            form=["L", "L", "W", "L", "L"],
            avg_scored=108.0, avg_conceded=117.0,
            home_avg_scored=110.5, home_avg_conceded=115.0,
            away_avg_scored=105.5, away_avg_conceded=119.5,
            rank=14,
            ht_avg_scored=53.0, ht_avg_conceded=58.0,
        ),
        h2h=HeadToHead(total_games=8, home_wins=7, away_wins=1, draws=0,
                       avg_total_goals=226.0, avg_ht_goals=112.5),
        handicap_line=-8.5, handicap_home_odds=1.90, handicap_away_odds=1.90,
        ht_over_line=111.5, ht_over_odds=1.87,
        ft_over_line=225.5, ft_over_odds=1.85,
    ),
    Game(
        id="bb_002",
        sport=Sport.BASKETBALL,
        league="NBA",
        home_team=TeamStats(
            name="Golden State Warriors",
            form=["W", "W", "L", "W", "W"],
            avg_scored=116.0, avg_conceded=111.0,
            home_avg_scored=119.5, home_avg_conceded=109.0,
            away_avg_scored=112.5, away_avg_conceded=113.5,
            rank=3,
            ht_avg_scored=58.0, ht_avg_conceded=55.0,
        ),
        away_team=TeamStats(
            name="Sacramento Kings",
            form=["W", "L", "W", "W", "L"],
            avg_scored=115.5, avg_conceded=113.5,
            home_avg_scored=118.0, home_avg_conceded=112.0,
            away_avg_scored=113.0, away_avg_conceded=115.5,
            rank=7,
            ht_avg_scored=57.5, ht_avg_conceded=56.5,
        ),
        h2h=HeadToHead(total_games=6, home_wins=4, away_wins=2, draws=0,
                       avg_total_goals=230.0, avg_ht_goals=115.0),
        handicap_line=-4.5, handicap_home_odds=1.90, handicap_away_odds=1.90,
        ht_over_line=114.5, ht_over_odds=1.88,
        ft_over_line=229.5, ft_over_odds=1.87,
    ),
    Game(
        id="bb_003",
        sport=Sport.BASKETBALL,
        league="NBA",
        home_team=TeamStats(
            name="Milwaukee Bucks",
            form=["W", "W", "W", "D", "W"],
            avg_scored=117.0, avg_conceded=110.5,
            home_avg_scored=120.5, home_avg_conceded=108.5,
            away_avg_scored=113.5, away_avg_conceded=113.0,
            rank=2,
            ht_avg_scored=59.0, ht_avg_conceded=54.5,
        ),
        away_team=TeamStats(
            name="Charlotte Hornets",
            form=["L", "L", "L", "W", "L"],
            avg_scored=106.5, avg_conceded=116.5,
            home_avg_scored=109.0, home_avg_conceded=114.5,
            away_avg_scored=104.0, away_avg_conceded=118.5,
            rank=13,
            ht_avg_scored=52.5, ht_avg_conceded=58.5,
        ),
        h2h=HeadToHead(total_games=6, home_wins=5, away_wins=1, draws=0,
                       avg_total_goals=223.0, avg_ht_goals=111.0),
        handicap_line=-10.5, handicap_home_odds=1.88, handicap_away_odds=1.92,
        ht_over_line=110.5, ht_over_odds=1.90,
        ft_over_line=221.5, ft_over_odds=1.85,
    ),
]


# ── TENNIS MATCHES ───────────────────────────────────────────────────────────
# avg_scored = avg games won per set, avg_conceded = avg games lost per set
# ht_avg_scored/conceded = set 1 games won/lost

TENNIS_MATCHES: list[Game] = [
    Game(
        id="tn_001",
        sport=Sport.TENNIS,
        league="ATP Masters",
        surface="clay",
        home_team=TeamStats(
            name="Carlos Alcaraz",
            form=["W", "W", "W", "L", "W"],
            avg_scored=5.8, avg_conceded=3.4,
            home_avg_scored=5.9, home_avg_conceded=3.2,
            away_avg_scored=5.6, away_avg_conceded=3.6,
            rank=2,
            ht_avg_scored=5.9, ht_avg_conceded=3.3,
        ),
        away_team=TeamStats(
            name="Alejandro Davidovich Fokina",
            form=["L", "W", "L", "W", "L"],
            avg_scored=4.8, avg_conceded=5.2,
            home_avg_scored=5.0, home_avg_conceded=5.0,
            away_avg_scored=4.6, away_avg_conceded=5.4,
            rank=35,
            ht_avg_scored=4.7, ht_avg_conceded=5.3,
        ),
        h2h=HeadToHead(total_games=5, home_wins=4, away_wins=1, draws=0,
                       avg_total_goals=22.0, avg_ht_goals=10.8),
        handicap_line=-1.5, handicap_home_odds=1.65, handicap_away_odds=2.30,
        ht_over_line=10.5,  ht_over_odds=1.90,
        ft_over_line=21.5,  ft_over_odds=1.85,
    ),
    Game(
        id="tn_002",
        sport=Sport.TENNIS,
        league="WTA",
        surface="hard",
        home_team=TeamStats(
            name="Iga Swiatek",
            form=["W", "W", "W", "W", "L"],
            avg_scored=5.9, avg_conceded=3.0,
            home_avg_scored=6.0, home_avg_conceded=2.9,
            away_avg_scored=5.8, away_avg_conceded=3.1,
            rank=1,
            ht_avg_scored=6.0, ht_avg_conceded=2.8,
        ),
        away_team=TeamStats(
            name="Elina Svitolina",
            form=["W", "L", "W", "L", "W"],
            avg_scored=5.0, avg_conceded=5.0,
            home_avg_scored=5.2, home_avg_conceded=4.8,
            away_avg_scored=4.8, away_avg_conceded=5.2,
            rank=22,
            ht_avg_scored=4.9, ht_avg_conceded=5.1,
        ),
        h2h=HeadToHead(total_games=7, home_wins=6, away_wins=1, draws=0,
                       avg_total_goals=20.5, avg_ht_goals=10.2),
        handicap_line=-1.5, handicap_home_odds=1.60, handicap_away_odds=2.40,
        ht_over_line=10.5,  ht_over_odds=1.88,
        ft_over_line=20.5,  ft_over_odds=1.87,
    ),
    Game(
        id="tn_003",
        sport=Sport.TENNIS,
        league="ATP Slam",
        surface="grass",
        home_team=TeamStats(
            name="Novak Djokovic",
            form=["W", "W", "L", "W", "W"],
            avg_scored=5.7, avg_conceded=3.2,
            home_avg_scored=5.8, home_avg_conceded=3.1,
            away_avg_scored=5.6, away_avg_conceded=3.3,
            rank=3,
            ht_avg_scored=5.8, ht_avg_conceded=3.0,
        ),
        away_team=TeamStats(
            name="Taylor Fritz",
            form=["W", "L", "W", "L", "W"],
            avg_scored=5.2, avg_conceded=4.8,
            home_avg_scored=5.4, home_avg_conceded=4.6,
            away_avg_scored=5.0, away_avg_conceded=5.0,
            rank=12,
            ht_avg_scored=5.1, ht_avg_conceded=4.9,
        ),
        h2h=HeadToHead(total_games=6, home_wins=5, away_wins=1, draws=0,
                       avg_total_goals=19.5, avg_ht_goals=9.5),
        handicap_line=-1.5, handicap_home_odds=1.70, handicap_away_odds=2.20,
        ht_over_line=9.5,   ht_over_odds=1.90,
        ft_over_line=19.5,  ft_over_odds=1.85,
    ),
]


def get_all_games() -> list[Game]:
    return FOOTBALL_GAMES + BASKETBALL_GAMES + TENNIS_MATCHES


def get_games_by_sport(sport: Sport) -> list[Game]:
    return [g for g in get_all_games() if g.sport == sport]
