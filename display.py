"""
Terminal display layer using only stdlib (no external deps required).
Falls back gracefully if `rich` is installed for enhanced output.
"""
import sys
import io

# Force UTF-8 output on Windows to handle box-drawing characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    from rich.text import Text
    RICH = True
    _console = Console()
except ImportError:
    RICH = False
    _console = None

from models import BetAnalysis, BetSlip, Sport, BetType, Game


# ─── ANSI helpers (used when rich is not available) ─────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
MAGENTA = "\033[95m"

SPORT_COLORS = {
    Sport.FOOTBALL:   CYAN,
    Sport.BASKETBALL: YELLOW,
    Sport.TENNIS:     GREEN,
}

CONF_COLORS = {
    "HIGH":   GREEN,
    "MEDIUM": YELLOW,
    "LOW":    RED,
}


def _conf_color(conf: str) -> str:
    return CONF_COLORS.get(conf, RESET)


def _prob_bar(prob: float, width: int = 20) -> str:
    filled = int(prob * width)
    bar = "#" * filled + "-" * (width - filled)
    pct = f"{prob:.0%}"
    return f"[{bar}] {pct}"


def print_header():
    title = "BET ANALYZER & BUILDER v1.0"
    subtitle = "Football · Basketball · Tennis"
    sep = "═" * 60
    if RICH:
        _console.print(Panel(
            f"[bold cyan]{title}[/bold cyan]\n[dim]{subtitle}[/dim]",
            border_style="cyan",
            expand=False,
        ))
    else:
        print(f"\n{CYAN}{BOLD}{sep}{RESET}")
        print(f"{CYAN}{BOLD}  {title}{RESET}")
        print(f"{BLUE}  {subtitle}{RESET}")
        print(f"{CYAN}{BOLD}{sep}{RESET}\n")


def print_section(title: str):
    if RICH:
        _console.rule(f"[bold yellow]{title}[/bold yellow]")
    else:
        print(f"\n{YELLOW}{BOLD}── {title} {'─' * (54 - len(title))}{RESET}")


def print_no_bets():
    msg = "No qualifying bets found (>=70% probability + positive EV)"
    if RICH:
        _console.print(f"[dim italic]{msg}[/dim italic]")
    else:
        print(f"  {RED}{msg}{RESET}")


def print_analysis_table(analyses: list[BetAnalysis]):
    """Print a table of recommended bet analyses."""
    if not analyses:
        print_no_bets()
        return

    if RICH:
        table = Table(box=box.ROUNDED, header_style="bold magenta", show_lines=True)
        table.add_column("Match", style="white", min_width=28)
        table.add_column("Sport", style="cyan", width=12)
        table.add_column("Bet Type", style="yellow", width=16)
        table.add_column("Line", justify="center", width=8)
        table.add_column("Odds", justify="center", width=7)
        table.add_column("Prob %", justify="center", width=9)
        table.add_column("EV", justify="center", width=9)
        table.add_column("Conf", justify="center", width=8)

        for a in analyses:
            g = a.game
            match = f"{g.home_team.name}\nvs {g.away_team.name}"
            prob_color = "green" if a.probability >= 0.78 else "yellow"
            ev_color = "green" if a.expected_value >= 0.05 else "yellow"
            conf_color = {"HIGH": "green", "MEDIUM": "yellow", "LOW": "red"}.get(a.confidence, "white")
            table.add_row(
                match,
                g.sport.value,
                a.bet_type.value,
                f"{a.line:+.1f}",
                str(a.odds),
                f"[{prob_color}]{a.probability:.0%}[/{prob_color}]",
                f"[{ev_color}]{a.expected_value:+.3f}[/{ev_color}]",
                f"[{conf_color}]{a.confidence}[/{conf_color}]",
            )
        _console.print(table)
    else:
        col = f"{'Match':<30} {'Sport':<12} {'Bet Type':<18} {'Line':>6} {'Odds':>6} {'Prob':>7} {'EV':>8} {'Conf':<8}"
        sep = "─" * len(col)
        print(f"\n  {BOLD}{col}{RESET}")
        print(f"  {sep}")
        for a in analyses:
            g = a.game
            match = f"{g.home_team.name} vs {g.away_team.name}"
            cc = _conf_color(a.confidence)
            pc = GREEN if a.probability >= 0.78 else YELLOW
            ec = GREEN if a.expected_value >= 0.05 else YELLOW
            line = (
                f"  {match:<30} {g.sport.value:<12} {a.bet_type.value:<18} "
                f"{a.line:>+6.1f} {a.odds:>6} "
                f"{pc}{a.probability:>6.0%}{RESET} "
                f"{ec}{a.expected_value:>+8.3f}{RESET} "
                f"{cc}{a.confidence:<8}{RESET}"
            )
            print(line)
        print()


def print_analysis_detail(analysis: BetAnalysis):
    """Print detailed reasoning for a single bet analysis."""
    g = analysis.game
    title = f"{g.home_team.name} vs {g.away_team.name}  [{g.sport.value}]"

    if RICH:
        body = "\n".join(f"  • {r}" for r in analysis.reasoning)
        _console.print(Panel(
            f"[bold]{analysis.bet_type.value}[/bold] — {analysis.side}\n\n{body}",
            title=f"[cyan]{title}[/cyan]",
            border_style="blue",
        ))
    else:
        print(f"\n  {CYAN}{BOLD}{title}{RESET}")
        print(f"  {BOLD}{analysis.bet_type.value}[/bold] — {analysis.side}")
        print(f"  {'─' * 50}")
        for r in analysis.reasoning:
            print(f"    • {r}")
        print()


def print_slip(slip: BetSlip, index: int = 1):
    """Print a single bet slip."""
    legs = len(slip.bets)
    label = "Single" if legs == 1 else f"{legs}-Leg Accumulator"

    if RICH:
        lines = []
        for i, bet in enumerate(slip.bets, 1):
            g = bet.game
            match = f"{g.home_team.name} vs {g.away_team.name}"
            lines.append(
                f"  [dim]Leg {i}:[/dim] [{g.sport.value}] [white]{match}[/white]\n"
                f"         [yellow]{bet.bet_type.value}[/yellow] [cyan]{bet.side}[/cyan]"
                f" @ [green]{bet.odds}[/green] ([bold]{bet.probability:.0%}[/bold])"
            )

        body = "\n".join(lines)
        prob_line = f"\n  [dim]Combined probability:[/dim] [bold]{slip.combined_probability:.0%}[/bold]" if legs > 1 else ""
        footer = (
            f"{prob_line}\n"
            f"  [dim]Combined odds:[/dim] [bold green]{slip.combined_odds}[/bold green]\n"
            f"  [dim]Stake:[/dim] ${slip.stake:.2f}  →  "
            f"[bold green]Potential payout: ${slip.potential_payout:.2f}[/bold green]"
        )
        _console.print(Panel(
            body + footer,
            title=f"[bold magenta]Slip #{index} — {label}[/bold magenta]",
            border_style="magenta",
        ))
    else:
        print(f"\n  {MAGENTA}{BOLD}── Slip #{index}: {label} {'─' * 30}{RESET}")
        for i, bet in enumerate(slip.bets, 1):
            g = bet.game
            match = f"{g.home_team.name} vs {g.away_team.name}"
            print(
                f"  Leg {i}: [{g.sport.value}] {match} | "
                f"{bet.bet_type.value} {bet.side} @ {bet.odds} ({bet.probability:.0%})"
            )
        if legs > 1:
            print(f"  Combined probability: {slip.combined_probability:.0%}")
        print(
            f"  {GREEN}Odds: {slip.combined_odds}  |  "
            f"Stake: ${slip.stake:.2f}  →  Payout: ${slip.potential_payout:.2f}{RESET}"
        )


def print_summary(total_games: int, total_recommended: int, stake: float):
    msg = (
        f"Analyzed {total_games} games | "
        f"{total_recommended} qualifying bets (≥70% prob + +EV) | "
        f"Stake per slip: ${stake:.2f}"
    )
    if RICH:
        _console.print(f"\n[bold green]Summary:[/bold green] [white]{msg}[/white]\n")
    else:
        print(f"\n  {GREEN}{BOLD}Summary:{RESET} {msg}\n")


def print_disclaimer():
    text = (
        "DISCLAIMER: This tool is for educational and entertainment purposes only.\n"
        "Probability estimates are model-based and do not guarantee outcomes.\n"
        "Bet responsibly. Check local laws before placing real money wagers."
    )
    if RICH:
        _console.print(Panel(f"[dim]{text}[/dim]", border_style="dim", expand=False))
    else:
        print(f"\n  {BOLD}{'─' * 60}{RESET}")
        for line in text.split("\n"):
            print(f"  {line}")
        print(f"  {BOLD}{'─' * 60}{RESET}\n")
