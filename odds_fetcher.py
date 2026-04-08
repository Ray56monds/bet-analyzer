"""
Real odds fetcher using The Odds API (https://the-odds-api.com).
Free tier: 500 requests/month.

Get your free key at: https://the-odds-api.com/#get-access
Set ODDS_API_KEY in your .env file.

Supported markets:
  - spreads  → Handicap
  - totals   → FT Over / HT Over (where available)

When no key is set, estimated odds from data_fetcher are used instead.
"""

import os
import json
import datetime
from pathlib import Path

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

ODDS_BASE = "https://api.the-odds-api.com/v4"
CACHE_DIR = Path(__file__).parent / ".cache"

# Map our sport/league to Odds API sport keys
SPORT_KEYS = {
    # Football
    "Premier League":    "soccer_epl",
    "La Liga":           "soccer_spain_la_liga",
    "Bundesliga":        "soccer_germany_bundesliga",
    "Serie A":           "soccer_italy_serie_a",
    "Ligue 1":           "soccer_france_ligue_one",
    "Champions League":  "soccer_uefa_champs_league",
    "Europa League":     "soccer_uefa_europa_league",
    "Conference League": "soccer_uefa_europa_conference_league",
    "Primeira Liga":     "soccer_portugal_primeira_liga",
    "Eredivisie":        "soccer_netherlands_eredivisie",
    # Basketball
    "NBA":               "basketball_nba",
    "Euroleague":        "basketball_euroleague",
    # Tennis
    "ATP":               "tennis_atp_aus_open_singles",  # generic fallback
}


def _odds_key() -> str | None:
    key = os.getenv("ODDS_API_KEY", "")
    return key if key and key != "your_odds_key_here" else None


def _cache_path(name: str) -> Path:
    today = datetime.date.today().isoformat()
    return CACHE_DIR / f"{today}_odds_{name}.json"


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


def _fetch_odds(sport_key: str) -> list[dict]:
    cached = _load_cache(sport_key)
    if cached is not None:
        return cached

    key = _odds_key()
    if not key or not REQUESTS_OK:
        return []

    try:
        resp = requests.get(
            f"{ODDS_BASE}/sports/{sport_key}/odds",
            params={
                "apiKey":     key,
                "regions":    "eu,uk",
                "markets":    "spreads,totals",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            _save_cache(sport_key, data)
            remaining = resp.headers.get("x-requests-remaining", "?")
            print(f"[ODDS] {sport_key}: {len(data)} events | {remaining} requests remaining")
            return data
        print(f"[ODDS] {sport_key} → HTTP {resp.status_code}")
    except Exception as e:
        print(f"[ODDS] Request failed: {e}")
    return []


def _normalize(name: str) -> str:
    """Lowercase and strip for fuzzy team name matching."""
    return name.lower().replace("fc ", "").replace(" fc", "").replace(".", "").strip()


def _find_event(events: list[dict], home: str, away: str) -> dict | None:
    h, a = _normalize(home), _normalize(away)
    for ev in events:
        eh = _normalize(ev.get("home_team", ""))
        ea = _normalize(ev.get("away_team", ""))
        if (h in eh or eh in h) and (a in ea or ea in a):
            return ev
    return None


def _best_decimal_odds(bookmakers: list[dict], market: str, outcome_name: str) -> float | None:
    """Pick the best (highest) decimal odds across all bookmakers for a given outcome."""
    best = None
    for bm in bookmakers:
        for mkt in bm.get("markets", []):
            if mkt["key"] != market:
                continue
            for outcome in mkt.get("outcomes", []):
                if _normalize(outcome["name"]) == _normalize(outcome_name):
                    odds = float(outcome["price"])
                    if best is None or odds > best:
                        best = odds
    return best


def enrich_game_with_real_odds(game) -> bool:
    """
    Look up real bookmaker odds for a game and update it in-place.
    Returns True if odds were found and applied.
    """
    if not _odds_key():
        return False

    sport_key = SPORT_KEYS.get(game.league or "")
    if not sport_key:
        return False

    events = _fetch_odds(sport_key)
    if not events:
        return False

    event = _find_event(events, game.home_team.name, game.away_team.name)
    if not event:
        return False

    bms = event.get("bookmakers", [])

    # Spread (handicap) odds
    spread_home = _best_decimal_odds(bms, "spreads", game.home_team.name)
    spread_away = _best_decimal_odds(bms, "spreads", game.away_team.name)

    # Totals (over/under)
    over_odds  = _best_decimal_odds(bms, "totals", "Over")
    under_odds = _best_decimal_odds(bms, "totals", "Under")

    # Extract spread point from first bookmaker that has it
    spread_point = None
    for bm in bms:
        for mkt in bm.get("markets", []):
            if mkt["key"] == "spreads":
                for outcome in mkt.get("outcomes", []):
                    if _normalize(outcome["name"]) == _normalize(game.home_team.name):
                        spread_point = outcome.get("point")
                        break
            if spread_point is not None:
                break
        if spread_point is not None:
            break

    total_point = None
    for bm in bms:
        for mkt in bm.get("markets", []):
            if mkt["key"] == "totals":
                for outcome in mkt.get("outcomes", []):
                    if outcome["name"] == "Over":
                        total_point = outcome.get("point")
                        break
            if total_point is not None:
                break
        if total_point is not None:
            break

    changed = False
    if spread_home and spread_point is not None:
        game.handicap_line       = float(spread_point)
        game.handicap_home_odds  = round(spread_home, 2)
        game.handicap_away_odds  = round(spread_away, 2) if spread_away else game.handicap_away_odds
        changed = True

    if over_odds and total_point is not None:
        game.ft_over_line  = float(total_point)
        game.ft_over_odds  = round(over_odds, 2)
        changed = True

    return changed


def enrich_all_games(games: list) -> int:
    """Enrich a list of Game objects with real odds. Returns count updated."""
    if not _odds_key():
        return 0
    updated = sum(1 for g in games if enrich_game_with_real_odds(g))
    if updated:
        print(f"[ODDS] Updated real odds for {updated}/{len(games)} game(s).")
    return updated
