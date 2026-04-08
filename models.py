"""
Data models for the Bet Analyzer system.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Sport(Enum):
    FOOTBALL = "Football"
    BASKETBALL = "Basketball"
    TENNIS = "Tennis"


class BetType(Enum):
    HANDICAP = "Handicap"
    HALFTIME_OVER = "Half Time Over"
    FULLTIME_OVER = "Full Time Over"


@dataclass
class TeamStats:
    name: str
    form: list[str]          # Last 5 results: 'W', 'D', 'L'
    avg_scored: float        # Average goals/points scored per game
    avg_conceded: float      # Average goals/points conceded per game
    home_avg_scored: float
    home_avg_conceded: float
    away_avg_scored: float
    away_avg_conceded: float
    rank: int                # League/ATP rank
    ht_avg_scored: float     # First half average scored (football/basketball)
    ht_avg_conceded: float   # First half average conceded

    @property
    def form_score(self) -> float:
        """Score from 0 to 1 based on last 5 results."""
        points = {"W": 1.0, "D": 0.5, "L": 0.0}
        if not self.form:
            return 0.5
        return sum(points.get(r, 0.0) for r in self.form[-5:]) / min(len(self.form), 5)


@dataclass
class HeadToHead:
    total_games: int
    home_wins: int
    away_wins: int
    draws: int
    avg_total_goals: float   # Average total goals/points in H2H
    avg_ht_goals: float      # Average first half goals/points in H2H


@dataclass
class Game:
    id: str
    sport: Sport
    home_team: TeamStats
    away_team: TeamStats
    h2h: HeadToHead
    is_home_match: bool = True
    surface: Optional[str] = None       # For tennis: 'clay', 'grass', 'hard'
    league: Optional[str] = None
    kick_off: Optional[str] = None      # ISO datetime string e.g. "2026-04-08T19:45:00+00:00"
    home_logo: Optional[str] = None     # URL to team/player logo
    away_logo: Optional[str] = None

    # Odds provided by any bookmaker
    handicap_line: float = 0.0        # e.g. -1.5 means home gives 1.5 goal start
    handicap_home_odds: float = 1.90
    handicap_away_odds: float = 1.90
    ht_over_line: float = 1.5         # First half over line
    ht_over_odds: float = 1.85
    ft_over_line: float = 2.5         # Full time over line
    ft_over_odds: float = 1.85


@dataclass
class BetAnalysis:
    game: Game
    bet_type: BetType
    line: float
    odds: float
    probability: float       # Calculated win probability 0-1
    confidence: str          # 'HIGH', 'MEDIUM', 'LOW'
    expected_value: float    # EV = (prob * odds) - 1
    reasoning: list[str] = field(default_factory=list)

    @property
    def is_recommended(self) -> bool:
        return self.probability >= 0.70 and self.expected_value > 0

    @property
    def side(self) -> str:
        if self.bet_type == BetType.HANDICAP:
            return f"Home ({self.game.home_team.name}) {self.line:+.1f}"
        elif self.bet_type == BetType.HALFTIME_OVER:
            return f"HT Over {self.line}"
        else:
            return f"FT Over {self.line}"


@dataclass
class BetSlip:
    bets: list[BetAnalysis] = field(default_factory=list)
    stake: float = 10.0

    @property
    def combined_odds(self) -> float:
        result = 1.0
        for b in self.bets:
            result *= b.odds
        return round(result, 2)

    @property
    def potential_payout(self) -> float:
        return round(self.stake * self.combined_odds, 2)

    @property
    def combined_probability(self) -> float:
        result = 1.0
        for b in self.bets:
            result *= b.probability
        return round(result, 4)
