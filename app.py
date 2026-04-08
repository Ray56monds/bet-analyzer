"""
Flask web app — Bet Analyzer Dashboard.

Run:
  python app.py

Then open: http://localhost:5000
"""

import os
import datetime
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

load_dotenv()

from models import Sport, BetType
from analyzer import analyze_all_games, rank_analyses
from bet_builder import build_singles, build_doubles, build_smart
from data_fetcher import get_all_today_games

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")


def _game_to_dict(game) -> dict:
    return {
        "id": game.id,
        "sport": game.sport.value,
        "league": game.league or "",
        "home": game.home_team.name,
        "away": game.away_team.name,
        "surface": game.surface,
    }


def _analysis_to_dict(analysis) -> dict:
    g = analysis.game
    return {
        "game_id": g.id,
        "sport": g.sport.value,
        "league": g.league or "",
        "home": g.home_team.name,
        "away": g.away_team.name,
        "bet_type": analysis.bet_type.value,
        "side": analysis.side,
        "line": analysis.line,
        "odds": analysis.odds,
        "probability": round(analysis.probability * 100, 1),
        "expected_value": round(analysis.expected_value * 100, 1),
        "confidence": analysis.confidence,
        "reasoning": analysis.reasoning,
        "surface": g.surface,
    }


def _slip_to_dict(slip, index: int) -> dict:
    return {
        "index": index,
        "legs": [_analysis_to_dict(b) for b in slip.bets],
        "combined_odds": slip.combined_odds,
        "combined_probability": round(slip.combined_probability * 100, 1),
        "stake": slip.stake,
        "potential_payout": slip.potential_payout,
        "label": "Single" if len(slip.bets) == 1 else f"{len(slip.bets)}-Leg Acca",
    }


@app.route("/")
def index():
    today = datetime.date.today().strftime("%A, %d %B %Y")
    return render_template("index.html", today=today)


@app.route("/api/analyze")
def api_analyze():
    sport_filter = request.args.get("sport", "all")
    min_prob = float(request.args.get("min_prob", 0.70))
    stake = float(request.args.get("stake", 10.0))

    games = get_all_today_games()

    # Filter by sport
    if sport_filter != "all":
        sport_map = {
            "football": Sport.FOOTBALL,
            "basketball": Sport.BASKETBALL,
            "tennis": Sport.TENNIS,
        }
        target = sport_map.get(sport_filter)
        if target:
            games = [g for g in games if g.sport == target]

    # Analyze
    results = analyze_all_games(games, min_prob=min_prob)
    all_bets = rank_analyses([b for bets in results.values() for b in bets])

    # Build slips
    singles = build_singles(all_bets, stake=stake)
    smart = build_smart(all_bets, stake=stake)

    return jsonify({
        "date": datetime.date.today().isoformat(),
        "total_games": len(games),
        "total_recommended": len(all_bets),
        "min_prob": min_prob,
        "bets": [_analysis_to_dict(b) for b in all_bets],
        "singles": [_slip_to_dict(s, i + 1) for i, s in enumerate(singles)],
        "smart_slips": [_slip_to_dict(s, i + 1) for i, s in enumerate(smart)],
    })


@app.route("/api/games")
def api_games():
    games = get_all_today_games()
    return jsonify({
        "date": datetime.date.today().isoformat(),
        "games": [_game_to_dict(g) for g in games],
        "count": len(games),
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("FLASK_PORT", 5000)))
    debug = os.getenv("RENDER") is None  # disable debug on Render
    print(f"\n  Bet Analyzer running at http://localhost:{port}\n")
    app.run(debug=debug, host="0.0.0.0", port=port)
