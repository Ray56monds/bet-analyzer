"""
Live data fetcher using API-Football (api-sports.io).

Free tier: 100 requests/day — https://dashboard.api-football.com/register
Set API_FOOTBALL_KEY in your .env file.

Falls back to sample_data if no key is configured.

Supported:
  - Football: today's fixtures + team stats + H2H
  - Basketball/Tennis: sample data (live APIs are sport-specific paid tiers)
"""

import os
import datetime
import json
from pathlib import Path

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

from models import Game, Sport, TeamStats, HeadToHead
import sample_data as demo

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://v3.football.api-sports.io"
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

# Top leagues to pull today's fixtures from (League IDs on api-football.com)
WATCHED_LEAGUES = {
    39:  ("Premier League",   "England"),
    140: ("La Liga",          "Spain"),
    78:  ("Bundesliga",       "Germany"),
    135: ("Serie A",          "Italy"),
    61:  ("Ligue 1",          "France"),
    2:   ("Champions League", "UEFA"),
    3:   ("Europa League",    "UEFA"),
    848: ("Conference League","UEFA"),
    94:  ("Primeira Liga",    "Portugal"),
    88:  ("Eredivisie",       "Netherlands"),
}

CURRENT_SEASON = 2024


def _api_key() -> str | None:
    key = os.getenv("API_FOOTBALL_KEY", "")
    return key if key and key != "your_api_key_here" else None


def _cache_path(name: str) -> Path:
    today = datetime.date.today().isoformat()
    return CACHE_DIR / f"{today}_{name}.json"


def _load_cache(name: str):
    p = _cache_path(name)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return None


def _save_cache(name: str, data):
    _cache_path(name).write_text(json.dumps(data))


def _get(endpoint: str, params: dict) -> dict | None:
    key = _api_key()
    if not key or not REQUESTS_OK:
        return None
    try:
        resp = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers={"x-apisports-key": key},
            params=params,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[API] Request failed: {e}")
    return None


# ── Fixture fetching ──────────────────────────────────────────────────────────

def fetch_today_fixtures() -> list[dict]:
    """Return raw fixture dicts for today from watched leagues."""
    cache_name = "fixtures_today"
    cached = _load_cache(cache_name)
    if cached is not None:
        return cached

    today = datetime.date.today().isoformat()
    all_fixtures = []

    for league_id in WATCHED_LEAGUES:
        data = _get("fixtures", {"date": today, "league": league_id, "status": "NS"})
        if data and "response" in data:
            all_fixtures.extend(data["response"])

    if all_fixtures:
        _save_cache(cache_name, all_fixtures)

    return all_fixtures


def fetch_team_stats(league_id: int, team_id: int) -> dict | None:
    cache_name = f"stats_{league_id}_{team_id}"
    cached = _load_cache(cache_name)
    if cached is not None:
        return cached

    data = _get("teams/statistics", {
        "league": league_id,
        "season": CURRENT_SEASON,
        "team": team_id,
    })
    if data and "response" in data:
        _save_cache(cache_name, data["response"])
        return data["response"]
    return None


def fetch_h2h(team1_id: int, team2_id: int, last: int = 10) -> list[dict]:
    cache_name = f"h2h_{team1_id}_{team2_id}"
    cached = _load_cache(cache_name)
    if cached is not None:
        return cached

    data = _get("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": last})
    fixtures = []
    if data and "response" in data:
        fixtures = data["response"]
        _save_cache(cache_name, fixtures)
    return fixtures


# ── Data mapping ──────────────────────────────────────────────────────────────

def _parse_form(fixtures: list[dict], team_id: int, last: int = 5) -> list[str]:
    """Extract W/D/L form from a list of played fixtures."""
    form = []
    played = [f for f in fixtures if f.get("fixture", {}).get("status", {}).get("short") == "FT"]
    for fix in played[-last:]:
        home_id = fix["teams"]["home"]["id"]
        home_goals = fix["goals"]["home"] or 0
        away_goals = fix["goals"]["away"] or 0
        if home_id == team_id:
            form.append("W" if home_goals > away_goals else ("D" if home_goals == away_goals else "L"))
        else:
            form.append("W" if away_goals > home_goals else ("D" if home_goals == away_goals else "L"))
    return form


def _safe(val, default=0.0):
    return float(val) if val is not None else default


def _build_team_stats(name: str, rank: int, stats: dict | None, form: list[str]) -> TeamStats:
    """Map API team statistics to our TeamStats model."""
    if stats is None:
        # Fallback: estimate by rank (lower rank = weaker team)
        base = max(0.5, 2.0 - rank * 0.05)
        return TeamStats(
            name=name, form=form,
            avg_scored=base, avg_conceded=2.5 - base,
            home_avg_scored=base + 0.2, home_avg_conceded=max(0.3, 2.5 - base - 0.2),
            away_avg_scored=max(0.3, base - 0.2), away_avg_conceded=2.5 - base + 0.2,
            rank=rank,
            ht_avg_scored=base * 0.42, ht_avg_conceded=(2.5 - base) * 0.42,
        )

    goals = stats.get("goals", {})
    scored_avg = _safe(goals.get("for", {}).get("average", {}).get("total"))
    conceded_avg = _safe(goals.get("against", {}).get("average", {}).get("total"))

    scored_home = _safe(goals.get("for", {}).get("average", {}).get("home"))
    conceded_home = _safe(goals.get("against", {}).get("average", {}).get("home"))
    scored_away = _safe(goals.get("for", {}).get("average", {}).get("away"))
    conceded_away = _safe(goals.get("against", {}).get("average", {}).get("away"))

    # First half goals (minute 0-45)
    ht_scored = _safe(goals.get("for", {}).get("minute", {}).get("0-15", {}).get("total", 0)) / 15 * 45 if False else scored_avg * 0.42
    ht_conceded = conceded_avg * 0.42

    # Better: use "minute" breakdown if available
    minute_for = goals.get("for", {}).get("minute", {})
    if minute_for:
        ht_buckets = ["0-15", "16-30", "31-45"]
        ht_scored_total = sum(
            _safe(minute_for.get(b, {}).get("total", 0)) for b in ht_buckets
        )
        played_total = _safe(stats.get("fixtures", {}).get("played", {}).get("total", 1)) or 1
        ht_scored = ht_scored_total / played_total

    minute_against = goals.get("against", {}).get("minute", {})
    if minute_against:
        ht_buckets = ["0-15", "16-30", "31-45"]
        ht_conceded_total = sum(
            _safe(minute_against.get(b, {}).get("total", 0)) for b in ht_buckets
        )
        played_total = _safe(stats.get("fixtures", {}).get("played", {}).get("total", 1)) or 1
        ht_conceded = ht_conceded_total / played_total

    return TeamStats(
        name=name, form=form,
        avg_scored=scored_avg or 1.2,
        avg_conceded=conceded_avg or 1.2,
        home_avg_scored=scored_home or scored_avg or 1.3,
        home_avg_conceded=conceded_home or conceded_avg or 1.1,
        away_avg_scored=scored_away or scored_avg or 1.1,
        away_avg_conceded=conceded_away or conceded_avg or 1.3,
        rank=rank,
        ht_avg_scored=ht_scored,
        ht_avg_conceded=ht_conceded,
    )


def _build_h2h(fixtures: list[dict], home_id: int) -> HeadToHead:
    """Compute H2H stats from raw fixture list."""
    total = len(fixtures)
    if total == 0:
        return HeadToHead(0, 0, 0, 0, 2.5, 1.0)

    home_wins = away_wins = draws = 0
    total_goals = total_ht_goals = 0

    for fix in fixtures:
        fhome_id = fix["teams"]["home"]["id"]
        hg = fix["goals"]["home"] or 0
        ag = fix["goals"]["away"] or 0
        total_goals += hg + ag

        # Rough first half estimate (API score object doesn't always have halftime)
        ht_score = fix.get("score", {}).get("halftime", {})
        ht_h = ht_score.get("home") or 0
        ht_a = ht_score.get("away") or 0
        total_ht_goals += (ht_h + ht_a) if (ht_h + ht_a) > 0 else (hg + ag) * 0.42

        winner = fix["teams"]["home"]["winner"]
        if winner is None:
            draws += 1
        elif (fhome_id == home_id and winner) or (fhome_id != home_id and not winner):
            home_wins += 1
        else:
            away_wins += 1

    return HeadToHead(
        total_games=total,
        home_wins=home_wins,
        away_wins=away_wins,
        draws=draws,
        avg_total_goals=round(total_goals / total, 2),
        avg_ht_goals=round(total_ht_goals / total, 2),
    )


def _default_odds(home_rank: int, away_rank: int) -> dict:
    """Estimate sensible odds when no live odds available."""
    strength_diff = (away_rank - home_rank) / 20.0
    handicap_line = round(min(2.5, max(-2.5, -strength_diff)), 1)
    return {
        "handicap_line": handicap_line,
        "handicap_home_odds": 1.90,
        "handicap_away_odds": 1.90,
        "ht_over_line": 0.5 if strength_diff > 1.0 else 1.5,
        "ht_over_odds": 1.80,
        "ft_over_line": 2.5,
        "ft_over_odds": 1.85,
    }


# ── Main public interface ─────────────────────────────────────────────────────

def get_today_football_games() -> list[Game]:
    """
    Return today's football games as Game objects ready for analysis.
    Uses live API if key is set, otherwise returns demo data.
    """
    key = _api_key()
    if not key:
        print("[INFO] No API_FOOTBALL_KEY found — using demo data.")
        print("[INFO] Get a free key at: https://dashboard.api-football.com/register")
        return demo.FOOTBALL_GAMES

    if not REQUESTS_OK:
        print("[WARN] `requests` not installed. Using demo data.")
        return demo.FOOTBALL_GAMES

    print(f"[API] Fetching today's fixtures ({datetime.date.today()})...")
    raw_fixtures = fetch_today_fixtures()

    if not raw_fixtures:
        print("[API] No fixtures found for today — using demo data.")
        return demo.FOOTBALL_GAMES

    print(f"[API] Found {len(raw_fixtures)} fixture(s). Fetching team stats...")

    games: list[Game] = []
    seen = set()

    for fix in raw_fixtures:
        try:
            fixture_id = fix["fixture"]["id"]
            if fixture_id in seen:
                continue
            seen.add(fixture_id)

            league_id = fix["league"]["id"]
            league_name = WATCHED_LEAGUES.get(league_id, ("Unknown", ""))[0]

            home = fix["teams"]["home"]
            away = fix["teams"]["away"]
            home_id, away_id = home["id"], away["id"]

            # Get team stats (cached after first call)
            home_stats_raw = fetch_team_stats(league_id, home_id)
            away_stats_raw = fetch_team_stats(league_id, away_id)

            # Get H2H
            h2h_fixtures = fetch_h2h(home_id, away_id)

            # Build form from H2H + recent fixtures (simplified)
            home_form = _parse_form(h2h_fixtures, home_id)
            away_form = _parse_form(h2h_fixtures, away_id)

            # Rank approximation from league standing (not fetched to save calls)
            home_rank = fix.get("league", {}).get("round", "Regular Season - 1").split("-")[-1].strip()
            home_rank = int(home_rank) if str(home_rank).isdigit() else 10
            away_rank = home_rank + 3

            home_team = _build_team_stats(home["name"], home_rank, home_stats_raw, home_form or ["W", "D", "W", "L", "W"])
            away_team = _build_team_stats(away["name"], away_rank, away_stats_raw, away_form or ["L", "W", "L", "D", "L"])
            h2h = _build_h2h(h2h_fixtures, home_id)

            odds = _default_odds(home_rank, away_rank)

            game = Game(
                id=f"live_{fixture_id}",
                sport=Sport.FOOTBALL,
                league=league_name,
                home_team=home_team,
                away_team=away_team,
                h2h=h2h,
                **odds,
            )
            games.append(game)

        except Exception as e:
            print(f"[WARN] Skipping fixture: {e}")
            continue

    print(f"[API] Built {len(games)} game model(s) for analysis.")
    return games if games else demo.FOOTBALL_GAMES


def get_all_today_games() -> list[Game]:
    """All sports: live football + demo basketball/tennis."""
    football = get_today_football_games()
    basketball = demo.BASKETBALL_GAMES   # Live NBA API requires separate key
    tennis = demo.TENNIS_MATCHES         # Live ATP/WTA API requires separate key
    return football + basketball + tennis
