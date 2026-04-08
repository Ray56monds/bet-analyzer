"""
Bet Builder — assembles recommended analyses into single bets and accumulators.

Strategies:
  - singles:  One bet per qualifying analysis
  - doubles:  All 2-leg combinations
  - trebles:  All 3-leg combinations
  - smart:    Auto-selects best EV combination up to `max_legs`
"""
from itertools import combinations
from models import BetAnalysis, BetSlip

# Minimum combined probability for multi-leg slips
DOUBLE_MIN_COMBINED_PROB = 0.55
TREBLE_MIN_COMBINED_PROB = 0.42


def build_singles(analyses: list[BetAnalysis], stake: float = 10.0) -> list[BetSlip]:
    """One slip per bet."""
    return [BetSlip(bets=[a], stake=stake) for a in analyses]


def build_doubles(analyses: list[BetAnalysis], stake: float = 10.0) -> list[BetSlip]:
    """All 2-leg combination slips that meet minimum combined probability."""
    slips = []
    for combo in combinations(analyses, 2):
        slip = BetSlip(bets=list(combo), stake=stake)
        if slip.combined_probability >= DOUBLE_MIN_COMBINED_PROB:
            slips.append(slip)
    return slips


def build_trebles(analyses: list[BetAnalysis], stake: float = 10.0) -> list[BetSlip]:
    """All 3-leg combination slips that meet minimum combined probability."""
    slips = []
    for combo in combinations(analyses, 3):
        slip = BetSlip(bets=list(combo), stake=stake)
        if slip.combined_probability >= TREBLE_MIN_COMBINED_PROB:
            slips.append(slip)
    return slips


def build_smart(analyses: list[BetAnalysis], stake: float = 10.0,
                max_legs: int = 4) -> list[BetSlip]:
    """
    Smart builder: picks the highest EV single, then greedily adds legs
    only if they keep combined probability above diminishing thresholds.
    Returns a ranked list: best single first, then accumulator if viable.
    """
    if not analyses:
        return []

    # Sort by EV desc
    ranked = sorted(analyses, key=lambda a: a.expected_value, reverse=True)
    slips: list[BetSlip] = []

    # Always add best single
    slips.append(BetSlip(bets=[ranked[0]], stake=stake))

    # Build accumulator greedily
    legs: list[BetAnalysis] = [ranked[0]]
    for candidate in ranked[1:]:
        if len(legs) >= max_legs:
            break
        trial = legs + [candidate]
        trial_prob = 1.0
        for a in trial:
            trial_prob *= a.probability
        # Threshold decays by leg
        min_prob = max(0.30, 0.70 ** len(trial))
        if trial_prob >= min_prob:
            legs = trial

    if len(legs) > 1:
        slips.append(BetSlip(bets=legs, stake=stake))

    return slips


def _ev_label(ev: float) -> str:
    if ev >= 0.15:
        return "EXCELLENT"
    if ev >= 0.05:
        return "GOOD"
    if ev > 0:
        return "MARGINAL"
    return "NEGATIVE"


def summarize_slip(slip: BetSlip) -> str:
    """Return a short human-readable summary of a bet slip."""
    lines = []
    for i, bet in enumerate(slip.bets, 1):
        game = bet.game
        matchup = f"{game.home_team.name} vs {game.away_team.name}"
        lines.append(
            f"  Leg {i}: [{game.sport.value}] {matchup} "
            f"| {bet.bet_type.value} {bet.side} "
            f"@ {bet.odds} ({bet.probability:.0%} prob)"
        )
    legs = len(slip.bets)
    label = "Single" if legs == 1 else f"{legs}-Leg Acca"
    combined = f"{slip.combined_probability:.0%}" if legs > 1 else ""
    prob_str = f" | Combined: {combined}" if combined else ""
    lines.insert(0, f"--- {label}{prob_str} | Odds: {slip.combined_odds} ---")
    lines.append(
        f"  Stake: ${slip.stake:.2f} | Potential Payout: ${slip.potential_payout:.2f}"
    )
    return "\n".join(lines)
