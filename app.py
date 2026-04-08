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

from models import Sport
from analyzer import analyze_all_games, rank_analyses
from bet_builder import build_singles, build_smart
from data_fetcher import get_all_today_games
from odds_fetcher import enrich_all_games
from notifier import subscribe, unsubscribe, send_alert

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_kickoff(iso: str) -> str:
    """Return HH:MM UTC string from ISO datetime, or empty string."""
    if not iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%H:%M UTC")
    except Exception:
        return ""


def _analysis_to_dict(analysis) -> dict:
    g = analysis.game
    return {
        "game_id":       g.id,
        "sport":         g.sport.value,
        "league":        g.league or "",
        "home":          g.home_team.name,
        "away":          g.away_team.name,
        "home_logo":     g.home_logo or "",
        "away_logo":     g.away_logo or "",
        "kick_off":      _fmt_kickoff(g.kick_off or ""),
        "surface":       g.surface or "",
        "bet_type":      analysis.bet_type.value,
        "side":          analysis.side,
        "line":          analysis.line,
        "odds":          analysis.odds,
        "probability":   round(analysis.probability * 100, 1),
        "expected_value":round(analysis.expected_value * 100, 1),
        "confidence":    analysis.confidence,
        "reasoning":     analysis.reasoning,
    }


def _slip_to_dict(slip, index: int) -> dict:
    return {
        "index":                index,
        "legs":                 [_analysis_to_dict(b) for b in slip.bets],
        "combined_odds":        slip.combined_odds,
        "combined_probability": round(slip.combined_probability * 100, 1),
        "stake":                slip.stake,
        "potential_payout":     slip.potential_payout,
        "label": "Single" if len(slip.bets) == 1 else f"{len(slip.bets)}-Leg Acca",
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    today = datetime.date.today().strftime("%A, %d %B %Y")
    has_odds_api  = bool(os.getenv("ODDS_API_KEY", ""))
    has_notify    = bool(os.getenv("NOTIFY_FROM", ""))
    return render_template("index.html",
                           today=today,
                           has_odds_api=has_odds_api,
                           has_notify=has_notify)


@app.route("/api/analyze")
def api_analyze():
    sport_filter = request.args.get("sport", "all")
    min_prob     = float(request.args.get("min_prob", 0.70))
    stake        = float(request.args.get("stake", 10.0))

    games = get_all_today_games()

    # Enrich with real bookmaker odds if ODDS_API_KEY is set
    enrich_all_games(games)

    # Sport filter
    if sport_filter != "all":
        sport_map = {
            "football":   Sport.FOOTBALL,
            "basketball": Sport.BASKETBALL,
            "tennis":     Sport.TENNIS,
        }
        target = sport_map.get(sport_filter)
        if target:
            games = [g for g in games if g.sport == target]

    results  = analyze_all_games(games, min_prob=min_prob)
    all_bets = rank_analyses([b for bets in results.values() for b in bets])
    smart    = build_smart(all_bets, stake=stake)

    return jsonify({
        "date":              datetime.date.today().isoformat(),
        "total_games":       len(games),
        "total_recommended": len(all_bets),
        "min_prob":          min_prob,
        "bets":              [_analysis_to_dict(b) for b in all_bets],
        "smart_slips":       [_slip_to_dict(s, i + 1) for i, s in enumerate(smart)],
        "real_odds":         bool(os.getenv("ODDS_API_KEY", "")),
    })


@app.route("/api/notify", methods=["POST"])
def api_notify():
    """Trigger alert emails for today's high-confidence bets."""
    games = get_all_today_games()
    enrich_all_games(games)
    results  = analyze_all_games(games, min_prob=0.70)
    all_bets = rank_analyses([b for bets in results.values() for b in bets])

    base_url = request.host_url.rstrip("/")
    result   = send_alert(all_bets, base_url=base_url)
    return jsonify(result)


@app.route("/subscribe", methods=["POST"])
def api_subscribe():
    email = request.json.get("email", "") if request.is_json else request.form.get("email", "")
    if subscribe(email):
        return jsonify({"ok": True, "message": f"Subscribed {email}"})
    return jsonify({"ok": False, "message": "Invalid email"}), 400


@app.route("/unsubscribe")
def api_unsubscribe():
    email = request.args.get("email", "")
    unsubscribe(email)
    return "<h3 style='font-family:sans-serif'>Unsubscribed successfully.</h3>"


if __name__ == "__main__":
    port  = int(os.getenv("PORT", os.getenv("FLASK_PORT", 5000)))
    debug = os.getenv("RENDER") is None
    print(f"\n  Bet Analyzer running at http://localhost:{port}\n")
    app.run(debug=debug, host="0.0.0.0", port=port)
