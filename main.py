"""
Bet Analyzer & Builder — Main Entry Point

Usage:
  python main.py                        # Analyze all sports, show singles + smart acca
  python main.py --sport football       # Football only
  python main.py --sport basketball     # Basketball only
  python main.py --sport tennis         # Tennis only
  python main.py --stake 20             # Set stake amount
  python main.py --min-prob 0.75        # Override 70% minimum threshold
  python main.py --mode singles         # Singles only
  python main.py --mode doubles         # Doubles (2-leg accumulators)
  python main.py --mode trebles         # Trebles (3-leg accumulators)
  python main.py --mode smart           # Auto-select best accumulator (default)
  python main.py --detail               # Show full reasoning for each bet
"""

import argparse
import sys

from models import Sport
from analyzer import analyze_all_games, rank_analyses
from bet_builder import build_singles, build_doubles, build_trebles, build_smart
from sample_data import get_all_games, get_games_by_sport
from display import (
    print_header, print_section, print_analysis_table,
    print_analysis_detail, print_slip, print_summary, print_disclaimer,
    print_no_bets,
)


SPORT_MAP = {
    "football":   Sport.FOOTBALL,
    "basketball": Sport.BASKETBALL,
    "tennis":     Sport.TENNIS,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bet Analyzer & Builder — Football, Basketball, Tennis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--sport", choices=["football", "basketball", "tennis", "all"],
        default="all", help="Filter by sport (default: all)"
    )
    parser.add_argument(
        "--stake", type=float, default=10.0,
        help="Stake amount per slip (default: $10)"
    )
    parser.add_argument(
        "--min-prob", type=float, default=0.70,
        help="Minimum win probability threshold (default: 0.70 = 70%%)"
    )
    parser.add_argument(
        "--mode", choices=["singles", "doubles", "trebles", "smart"],
        default="smart", help="Bet builder mode (default: smart)"
    )
    parser.add_argument(
        "--detail", action="store_true",
        help="Show detailed reasoning for each recommended bet"
    )
    parser.add_argument(
        "--top", type=int, default=0,
        help="Show only top N recommended bets (0 = all)"
    )
    return parser.parse_args()


def run(args: argparse.Namespace):
    print_header()

    # ── Load games ────────────────────────────────────────────────────────────
    if args.sport == "all":
        games = get_all_games()
    else:
        games = get_games_by_sport(SPORT_MAP[args.sport])

    if not games:
        print("No games found for the selected filter.")
        sys.exit(0)

    # ── Analyze ───────────────────────────────────────────────────────────────
    results = analyze_all_games(games, min_prob=args.min_prob)

    # Flatten all recommended bets into one ranked list
    all_recommended: list = []
    for bets in results.values():
        all_recommended.extend(bets)
    all_recommended = rank_analyses(all_recommended)

    if args.top > 0:
        all_recommended = all_recommended[: args.top]

    # ── Display analysis table ────────────────────────────────────────────────
    threshold_pct = f"{args.min_prob:.0%}"
    print_section(f"Recommended Bets  (≥{threshold_pct} Probability + Positive EV)")
    print_analysis_table(all_recommended)

    if not all_recommended:
        print_summary(len(games), 0, args.stake)
        print_disclaimer()
        return

    # ── Optional detail view ──────────────────────────────────────────────────
    if args.detail:
        print_section("Detailed Reasoning")
        for analysis in all_recommended:
            print_analysis_detail(analysis)

    # ── Build slips ───────────────────────────────────────────────────────────
    print_section(f"Bet Slips  [{args.mode.upper()} mode]  —  Stake: ${args.stake:.2f}")

    if args.mode == "singles":
        slips = build_singles(all_recommended, stake=args.stake)
    elif args.mode == "doubles":
        slips = build_doubles(all_recommended, stake=args.stake)
    elif args.mode == "trebles":
        slips = build_trebles(all_recommended, stake=args.stake)
    else:  # smart (default)
        slips = build_smart(all_recommended, stake=args.stake)

    if not slips:
        print_no_bets()
    else:
        for i, slip in enumerate(slips, 1):
            print_slip(slip, index=i)

    # ── Summary ───────────────────────────────────────────────────────────────
    print_summary(len(games), len(all_recommended), args.stake)
    print_disclaimer()


def main():
    args = parse_args()

    if args.min_prob < 0.50 or args.min_prob > 0.99:
        print("Error: --min-prob must be between 0.50 and 0.99")
        sys.exit(1)

    run(args)


if __name__ == "__main__":
    main()
