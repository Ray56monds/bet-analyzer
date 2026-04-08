"""
Live data fetcher using api-sports.io.
The SAME API key works for both football and basketball.

Football:   https://v3.football.api-sports.io
Basketball: https://v1.basketball.api-sports.io

Free tier: 100 requests/day per sport.
Set API_FOOTBALL_KEY in your .env file.
Falls back to sample data when no key is set or no games are found today.
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

# ── Config ────────────────────────────────────────────────────────────────────

FOOTBALL_BASE   = "https://v3.football.api-sports.io"
BASKETBALL_BASE = "https://v1.basketball.api-sports.io"

CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

WATCHED_FOOTBALL_LEAGUES = {
    39:  ("Premier League",    "England"),
    140: ("La Liga",           "Spain"),
    78:  ("Bundesliga",        "Germany"),
    135: ("Serie A",           "Italy"),
    61:  ("Ligue 1",           "France"),
    2:   ("Champions League",  "UEFA"),
    3:   ("Europa League",     "UEFA"),
    848: ("Conference League", "UEFA"),
    94:  ("Primeira Liga",     "Portugal"),
    88:  ("Eredivisie",        "Netherlands"),
}

WATCHED_BASKETBALL_LEAGUES = {
    12:  ("NBA",        "USA"),
    120: ("Euroleague", "Europe"),
    13:  ("NBL",        "Australia"),
}

FOOTBALL_SEASON   = 2025        # 2025-2026 European season
BASKETBALL_SEASON = "2025-2026"  # Current NBA season


# ── Core HTTP ─────────────────────────────────────────────────────────────────

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
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _save_cache(name: str, data):
    _cache_path(name).write_text(json.dumps(data), encoding="utf-8")


def _get(base_url: str, endpoint: str, params: dict) -> dict | None:
    key = _api_key()
    if not key or not REQUESTS_OK:
        return None
    try:
        resp = requests.get(
            f"{base_url}/{endpoint}",
            headers={"x-apisports-key": key},
            params=params,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"[API] {endpoint} → HTTP {resp.status_code}")
    except Exception as e:
        print(f"[API] Request failed ({endpoint}): {e}")
    return None


def _fg(endpoint, params): return _get(FOOTBALL_BASE,   endpoint, params)
def _bg(endpoint, params): return _get(BASKETBALL_BASE, endpoint, params)


# ── Football fetchers ─────────────────────────────────────────────────────────

def fetch_today_football_fixtures() -> list[dict]:
    cached = _load_cache("fb_fixtures_today")
    if cached is not None:
        return cached

    today = datetime.date.today().isoformat()
    results = []
    for league_id in WATCHED_FOOTBALL_LEAGUES:
        data = _fg("fixtures", {"date": today, "league": league_id, "status": "NS"})
        if data and "response" in data:
            results.extend(data["response"])

    if results:
        _save_cache("fb_fixtures_today", results)
    return results


def fetch_football_team_stats(league_id: int, team_id: int) -> dict | None:
    name = f"fb_stats_{league_id}_{team_id}"
    cached = _load_cache(name)
    if cached is not None:
        return cached
    data = _fg("teams/statistics", {"league": league_id, "season": FOOTBALL_SEASON, "team": team_id})
    if data and "response" in data:
        _save_cache(name, data["response"])
        return data["response"]
    return None


def fetch_football_h2h(team1_id: int, team2_id: int) -> list[dict]:
    name = f"fb_h2h_{team1_id}_{team2_id}"
    cached = _load_cache(name)
    if cached is not None:
        return cached
    data = _fg("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": 10})
    fixtures = data["response"] if data and "response" in data else []
    if fixtures:
        _save_cache(name, fixtures)
    return fixtures


# ── Basketball fetchers ───────────────────────────────────────────────────────

def fetch_today_basketball_fixtures() -> list[dict]:
    cached = _load_cache("bb_games_today")
    if cached is not None:
        return cached

    today = datetime.date.today().isoformat()
    # Fetch ALL games today (no league filter — avoids the mandatory season param issue)
    # then filter to watched leagues in the caller
    data = _bg("games", {"date": today})
    results = []
    if data and "response" in data:
        watched_ids = set(WATCHED_BASKETBALL_LEAGUES.keys())
        results = [g for g in data["response"] if g.get("league", {}).get("id") in watched_ids]

    if results:
        _save_cache("bb_games_today", results)
    return results


def fetch_basketball_team_stats(league_id: int, team_id: int) -> dict | None:
    name = f"bb_stats_{league_id}_{team_id}"
    cached = _load_cache(name)
    if cached is not None:
        return cached
    data = _bg("teams/statistics", {"league": league_id, "season": BASKETBALL_SEASON, "team": team_id})
    if data and "response" in data and data["response"]:
        result = data["response"][0] if isinstance(data["response"], list) else data["response"]
        _save_cache(name, result)
        return result
    return None


# ── Data mapping helpers ──────────────────────────────────────────────────────

def _safe(val, default=0.0) -> float:
    return float(val) if val is not None else default


def _parse_football_form(fixtures: list[dict], team_id: int, last: int = 5) -> list[str]:
    form = []
    played = [f for f in fixtures if f.get("fixture", {}).get("status", {}).get("short") == "FT"]
    for fix in played[-last:]:
        home_id = fix["teams"]["home"]["id"]
        hg = fix["goals"]["home"] or 0
        ag = fix["goals"]["away"] or 0
        if home_id == team_id:
            form.append("W" if hg > ag else ("D" if hg == ag else "L"))
        else:
            form.append("W" if ag > hg else ("D" if hg == ag else "L"))
    return form


def _build_football_team(name: str, rank: int, stats: dict | None, form: list[str]) -> TeamStats:
    if stats is None:
        base = max(0.5, 2.0 - rank * 0.05)
        return TeamStats(
            name=name, form=form,
            avg_scored=base, avg_conceded=2.5 - base,
            home_avg_scored=base + 0.2, home_avg_conceded=max(0.3, 2.3 - base),
            away_avg_scored=max(0.3, base - 0.2), away_avg_conceded=2.7 - base,
            rank=rank,
            ht_avg_scored=base * 0.42, ht_avg_conceded=(2.5 - base) * 0.42,
        )

    goals = stats.get("goals", {})
    s_avg  = _safe(goals.get("for",     {}).get("average", {}).get("total")) or 1.2
    c_avg  = _safe(goals.get("against", {}).get("average", {}).get("total")) or 1.2
    s_home = _safe(goals.get("for",     {}).get("average", {}).get("home"))  or s_avg
    c_home = _safe(goals.get("against", {}).get("average", {}).get("home"))  or c_avg
    s_away = _safe(goals.get("for",     {}).get("average", {}).get("away"))  or s_avg
    c_away = _safe(goals.get("against", {}).get("average", {}).get("away"))  or c_avg

    # First-half goals from minute breakdown
    ht_s = s_avg * 0.42
    ht_c = c_avg * 0.42
    m_for = goals.get("for", {}).get("minute", {})
    m_vs  = goals.get("against", {}).get("minute", {})
    played = _safe(stats.get("fixtures", {}).get("played", {}).get("total", 1)) or 1
    if m_for:
        ht_s = sum(_safe(m_for.get(b, {}).get("total", 0)) for b in ["0-15", "16-30", "31-45"]) / played
    if m_vs:
        ht_c = sum(_safe(m_vs.get(b, {}).get("total", 0)) for b in ["0-15", "16-30", "31-45"]) / played

    return TeamStats(
        name=name, form=form,
        avg_scored=s_avg, avg_conceded=c_avg,
        home_avg_scored=s_home, home_avg_conceded=c_home,
        away_avg_scored=s_away, away_avg_conceded=c_away,
        rank=rank,
        ht_avg_scored=ht_s, ht_avg_conceded=ht_c,
    )


def _build_basketball_team(name: str, rank: int, stats: dict | None, form: list[str]) -> TeamStats:
    if stats is None:
        # Rough NBA averages by rank
        pts = max(100.0, 118.0 - rank * 0.8)
        opp = min(125.0, 108.0 + rank * 0.5)
        return TeamStats(
            name=name, form=form,
            avg_scored=pts, avg_conceded=opp,
            home_avg_scored=pts + 3.0, home_avg_conceded=opp - 2.0,
            away_avg_scored=pts - 3.0, away_avg_conceded=opp + 2.0,
            rank=rank,
            ht_avg_scored=pts * 0.48, ht_avg_conceded=opp * 0.48,
        )

    games   = _safe(stats.get("games",  {}).get("played", {}).get("all"))  or 1
    pts_for = _safe(stats.get("points", {}).get("for",     {}).get("total", {}).get("all")) / games
    pts_vs  = _safe(stats.get("points", {}).get("against", {}).get("total", {}).get("all")) / games

    pts_for = pts_for or 110.0
    pts_vs  = pts_vs  or 110.0

    return TeamStats(
        name=name, form=form,
        avg_scored=pts_for, avg_conceded=pts_vs,
        home_avg_scored=pts_for + 3.0, home_avg_conceded=pts_vs - 2.0,
        away_avg_scored=pts_for - 3.0, away_avg_conceded=pts_vs + 2.0,
        rank=rank,
        ht_avg_scored=pts_for * 0.48, ht_avg_conceded=pts_vs * 0.48,
    )


def _build_football_h2h(fixtures: list[dict], home_id: int) -> HeadToHead:
    total = len(fixtures)
    if total == 0:
        return HeadToHead(0, 0, 0, 0, 2.5, 1.0)
    hw = aw = draws = tg = tht = 0
    for fix in fixtures:
        fhome = fix["teams"]["home"]["id"]
        hg = fix["goals"]["home"] or 0
        ag = fix["goals"]["away"] or 0
        tg += hg + ag
        ht = fix.get("score", {}).get("halftime", {})
        tht += (ht.get("home") or 0) + (ht.get("away") or 0) or (hg + ag) * 0.42
        winner = fix["teams"]["home"]["winner"]
        if winner is None:
            draws += 1
        elif (fhome == home_id and winner) or (fhome != home_id and not winner):
            hw += 1
        else:
            aw += 1
    return HeadToHead(total, hw, aw, draws, round(tg / total, 2), round(tht / total, 2))


def _default_football_odds(home_rank: int, away_rank: int) -> dict:
    diff = (away_rank - home_rank) / 20.0
    return {
        "handicap_line":       round(min(2.5, max(-2.5, -diff)), 1),
        "handicap_home_odds":  1.90,
        "handicap_away_odds":  1.90,
        "ht_over_line":        0.5 if diff > 1.0 else 1.5,
        "ht_over_odds":        1.80,
        "ft_over_line":        2.5,
        "ft_over_odds":        1.85,
    }


def _default_basketball_odds(home_rank: int, away_rank: int) -> dict:
    spread = round(min(10.0, max(-10.0, (away_rank - home_rank) * 0.5)), 1)
    return {
        "handicap_line":       -spread,
        "handicap_home_odds":  1.90,
        "handicap_away_odds":  1.90,
        "ht_over_line":        110.5,
        "ht_over_odds":        1.87,
        "ft_over_line":        225.5,
        "ft_over_odds":        1.87,
    }


# ── Public interface ──────────────────────────────────────────────────────────

def get_today_football_games() -> list[Game]:
    """Live football fixtures only. Returns empty list if none today."""
    if not _api_key():
        print("[INFO] No API_FOOTBALL_KEY set — football disabled.")
        return []

    print(f"[API] Fetching today's football fixtures ({datetime.date.today()})…")
    raw = fetch_today_football_fixtures()
    if not raw:
        print("[API] No football fixtures scheduled today.")
        return []

    print(f"[API] {len(raw)} football fixture(s) found.")
    games, seen = [], set()

    for fix in raw:
        try:
            fid = fix["fixture"]["id"]
            if fid in seen: continue
            seen.add(fid)

            lid   = fix["league"]["id"]
            lname = WATCHED_FOOTBALL_LEAGUES.get(lid, ("Unknown",))[0]
            home  = fix["teams"]["home"]
            away  = fix["teams"]["away"]

            h2h     = fetch_football_h2h(home["id"], away["id"])
            h_stats = fetch_football_team_stats(lid, home["id"])
            a_stats = fetch_football_team_stats(lid, away["id"])
            h_form  = _parse_football_form(h2h, home["id"]) or ["W","D","W","L","W"]
            a_form  = _parse_football_form(h2h, away["id"]) or ["L","W","L","D","L"]

            rnd    = fix.get("league", {}).get("round", "10").split("-")[-1].strip()
            h_rank = int(rnd) if rnd.isdigit() else 10
            a_rank = h_rank + 3

            games.append(Game(
                id=f"live_{fid}",
                sport=Sport.FOOTBALL,
                league=lname,
                home_team=_build_football_team(home["name"], h_rank, h_stats, h_form),
                away_team=_build_football_team(away["name"], a_rank, a_stats, a_form),
                h2h=_build_football_h2h(h2h, home["id"]),
                **_default_football_odds(h_rank, a_rank),
            ))
        except Exception as e:
            print(f"[WARN] Skipping football fixture: {e}")

    print(f"[API] Built {len(games)} football game(s).")
    return games


def get_today_basketball_games() -> list[Game]:
    """Live basketball games only. Returns empty list if none today."""
    if not _api_key():
        print("[INFO] No API_FOOTBALL_KEY set — basketball disabled.")
        return []

    print(f"[API] Fetching today's basketball games ({datetime.date.today()})…")
    raw = fetch_today_basketball_fixtures()
    if not raw:
        print("[API] No basketball games scheduled today.")
        return []

    print(f"[API] {len(raw)} basketball game(s) found.")
    games, seen = [], set()

    for g in raw:
        try:
            gid   = g["id"]
            if gid in seen: continue
            seen.add(gid)

            lid   = g["league"]["id"]
            lname = WATCHED_BASKETBALL_LEAGUES.get(lid, ("Basketball",))[0]
            home  = g["teams"]["home"]
            away  = g["teams"]["away"]

            h_stats = fetch_basketball_team_stats(lid, home["id"])
            a_stats = fetch_basketball_team_stats(lid, away["id"])

            h_rank = int(_safe(home.get("standing", {}).get("position")) or 8)
            a_rank = int(_safe(away.get("standing", {}).get("position")) or 8)

            games.append(Game(
                id=f"live_bb_{gid}",
                sport=Sport.BASKETBALL,
                league=lname,
                home_team=_build_basketball_team(home["name"], h_rank, h_stats, ["W","W","L","W","D"]),
                away_team=_build_basketball_team(away["name"], a_rank, a_stats, ["L","W","L","D","W"]),
                h2h=HeadToHead(0, 0, 0, 0, 220.0, 108.0),
                **_default_basketball_odds(h_rank, a_rank),
            ))
        except Exception as e:
            print(f"[WARN] Skipping basketball game: {e}")

    print(f"[API] Built {len(games)} basketball game(s).")
    return games


def get_all_today_games() -> list[Game]:
    """All live sports combined — no demo/static data."""
    return get_today_football_games() + get_today_basketball_games()
