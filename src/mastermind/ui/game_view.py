"""Modern terminal game view rendering board states, history, and status banners."""

from __future__ import annotations
import math
from typing import Optional, Sequence
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from rich import box

from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback, Observation
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.heuristic import DetailedGuessAnalysis, PartitionOutcome
from mastermind.telemetry import GuessScore, SearchTelemetry, SolverResult
from mastermind.ui.formatters import format_code, format_feedback, format_peg


def render_header(config: GameConfig, title: str = "MASTERMIND AI") -> Panel:
    """Render a modern header summarizing match configuration."""
    repeats_str = "[bold green]Allowed[/]" if config.allow_repeats else "[bold yellow]Prohibited[/]"
    max_str = f"[bold cyan]{config.max_guesses}[/]" if config.max_guesses else "[bold cyan]Unlimited[/]"
    seed_str = f" | Seed: [bold magenta]{config.seed}[/]" if config.seed is not None else ""

    info = (
        f"[bold]Pegs:[/] [bold cyan]{config.num_pegs}[/]  |  "
        f"[bold]Colors:[/] [bold cyan]{config.num_colors}[/]  |  "
        f"[bold]Repeats:[/] {repeats_str}  |  "
        f"[bold]Max Turns:[/] {max_str}"
        f"{seed_str}"
    )

    return Panel(
        Text.from_markup(f"[bold bright_white]{title}[/bold bright_white]\n[dim]{info}[/dim]", justify="center"),
        box=box.ROUNDED,
        style="bright_blue",
    )


def render_color_legend(config: GameConfig) -> Panel:
    """Render a toolbar legend showing all legal colors and tokens."""
    items = []
    for i in range(config.num_colors):
        items.append(format_peg(i, config, show_label=True))
    legend_text = "   ".join(items)

    return Panel(
        Text.from_markup(f"[bold]Available Colors:[/] {legend_text}\n[dim]Input format: integers (e.g. 0 1 2 3) or letters (e.g. R G B Y)[/dim]", justify="center"),
        box=box.SIMPLE,
        style="dim",
    )


def render_board(observation: Observation) -> Table:
    """Render the full Mastermind board table with turns and feedback."""
    config = observation.config
    table = Table(
        title=f"Game Board (Turn {observation.turn_number}" + (f" of {config.max_guesses})" if config.max_guesses else ")"),
        box=box.ROUNDED,
        header_style="bold bright_cyan",
        title_style="bold bright_white",
        expand=True,
    )

    table.add_column("Turn", justify="center", style="bold", width=6)
    table.add_column("Guess Code", justify="center", ratio=3)
    table.add_column("Feedback Pegs", justify="left", ratio=3)
    table.add_column("Exact", justify="center", style="bold red", width=7)
    table.add_column("Misplaced", justify="center", style="bold white", width=11)

    # Render completed turns
    for record in observation.history:
        guess_str = format_code(record.guess, config)
        fb_pegs = format_feedback(record.feedback, config.num_pegs)
        table.add_row(
            f"{record.turn:02d}",
            guess_str,
            fb_pegs,
            str(record.feedback.exact),
            str(record.feedback.misplaced),
        )

    # Render upcoming empty turn slots if max_guesses is set
    if config.max_guesses:
        for t in range(observation.turn_number + 1, config.max_guesses + 1):
            dim_pegs = " ".join(["[dim]·[/]"] * config.num_pegs)
            table.add_row(
                f"[dim]{t:02d}[/dim]",
                f"[dim]{dim_pegs}[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
            )

    return table


def render_telemetry_panel(telemetry: SearchTelemetry) -> Panel:
    """Render a clean telemetry panel displaying solver metrics and reasoning."""
    stats = (
        f"[bold cyan]Algorithm:[/] {telemetry.method_name}  |  "
        f"[bold cyan]Objective:[/] {telemetry.objective}\n"
        f"[bold]Candidates:[/] [bold yellow]{telemetry.initial_candidates_count}[/]  |  "
        f"[bold]Guesses Evaluated:[/] [bold yellow]{telemetry.guesses_considered_count}[/]  |  "
        f"[bold]Nodes:[/] [bold yellow]{telemetry.nodes_evaluated}[/]  |  "
        f"[bold]Latency:[/] [bold green]{telemetry.elapsed_time_ms:.2f} ms[/]\n"
        f"[bold]Status:[/] {'[bold green]Exact Optimal[/]' if telemetry.is_exact else '[bold yellow]Heuristic/Approx[/]'}  |  "
        f"[bold]Reason:[/] [dim]{telemetry.stopping_reason}[/dim]"
    )

    top_text = ""
    if telemetry.top_guesses:
        rows = []
        for rank, g in enumerate(telemetry.top_guesses[:3], 1):
            cand_badge = "[green](cand)[/]" if g.is_candidate else "[dim](non-cand)[/]"
            rows.append(
                f"  #{rank}: [bold]{g.guess}[/] {cand_badge} "
                f"| score: [bold cyan]{g.score:.3f}[/] "
                f"| worst-case rem: [bold red]{g.worst_case_remaining}[/] "
                f"| exp rem: [bold magenta]{g.expected_remaining:.2f}[/]"
            )
        top_text = "\n[bold bright_white]Top Considered Guesses:[/bold bright_white]\n" + "\n".join(rows)

    return Panel(
        Text.from_markup(f"{stats}{top_text}"),
        title="[bold bright_magenta]AI Solver Telemetry & Search Reasoning[/bold bright_magenta]",
        box=box.ROUNDED,
        style="bright_magenta",
    )


def render_status(observation: Observation, secret: Optional[Code] = None) -> Panel:
    """Render an end-of-game summary or in-progress turn banner."""
    config = observation.config

    if observation.is_solved:
        secret_display = format_code(secret, config) if secret else ""
        content = (
            f"[bold bright_green]VICTORY! CODE CRACKED![/bold bright_green]\n"
            f"Successfully cracked in [bold]{observation.turn_number}[/] turn(s)!\n"
            + (f"Secret Code: {secret_display}" if secret else "")
        )
        return Panel(
            Text.from_markup(content, justify="center"),
            box=box.DOUBLE,
            style="green",
        )
    elif observation.is_terminal:
        secret_display = format_code(secret, config) if secret else ""
        content = (
            f"[bold bright_red]GAME OVER! OUT OF GUESSES![/bold bright_red]\n"
            f"Reached limit of [bold]{config.max_guesses}[/] turn(s).\n"
            + (f"Secret Code was: {secret_display}" if secret else "")
        )
        return Panel(
            Text.from_markup(content, justify="center"),
            box=box.DOUBLE,
            style="red",
        )
    else:
        rem = observation.remaining_guesses
        rem_str = f"({rem} remaining)" if rem is not None else ""
        content = f"[bold cyan]Turn {observation.turn_number + 1}[/bold cyan] in progress... {rem_str}"
        return Panel(
            Text.from_markup(content, justify="center"),
            box=box.SIMPLE,
            style="cyan",
        )


def render_ai_hint(result: SolverResult, config: GameConfig) -> Panel:
    """Render an interactive hint panel for a human player."""
    tel = result.telemetry
    guess_display = format_code(result.guess, config)
    entropy_str = f"{-tel.best_score:.3f}" if tel.best_score < 0 else f"{tel.best_score:.3f}"

    lines = [
        f"[bold bright_green]Recommended Move:[/] {guess_display}",
        f"[bold cyan]Strategy:[/] {tel.method_name}  |  [bold cyan]Objective:[/] {tel.objective}",
        f"[bold]Information Gain (Entropy):[/] [bold yellow]{entropy_str} bits[/]  |  "
        f"[bold]Nodes Evaluated:[/] [bold yellow]{tel.nodes_evaluated}[/]",
        f"[bold]Search Latency:[/] [bold green]{tel.elapsed_time_ms:.2f} ms[/]  |  "
        f"[bold]Status:[/] [dim]{tel.stopping_reason}[/dim]",
    ]

    return Panel(
        Text.from_markup("\n".join(lines)),
        title="[bold bright_yellow]AI Tactical Hint[/bold bright_yellow]",
        box=box.ROUNDED,
        style="bright_yellow",
    )


def render_detailed_guess_eval(analysis: DetailedGuessAnalysis, config: GameConfig) -> Panel:
    """Render detailed information-theoretic evaluation and distribution frequencies for any guess."""
    guess_display = format_code(analysis.guess, config)
    cand_badge = "[bold green]Candidate Secret (Eligible to Win)[/]" if analysis.is_candidate else "[dim yellow]Probe Only (Eliminates Candidates)[/]"

    summary = (
        f"[bold bright_white]Evaluated Guess:[/] {guess_display}  {cand_badge}\n"
        f"[bold]Shannon Entropy:[/] [bold cyan]{analysis.entropy_bits:.4f} bits[/]  |  "
        f"[bold]Expected Remaining:[/] [bold magenta]{analysis.expected_remaining:.2f} codes[/]  |  "
        f"[bold]Worst-Case Remaining:[/] [bold red]{analysis.worst_case_remaining} codes[/]\n"
        f"[bold]Total Candidates Partitioned:[/] [bold yellow]{analysis.total_candidates}[/] into [bold yellow]{analysis.partition_count}[/] distinct feedback buckets\n"
    )

    table = Table(
        title="Feedback Distribution Frequencies & Probabilities",
        box=box.SIMPLE_HEAVY,
        header_style="bold bright_cyan",
        expand=True,
    )
    table.add_column("Feedback", justify="center", width=12)
    table.add_column("Exact (●)", justify="center", style="bold red", width=10)
    table.add_column("Misplaced (○)", justify="center", style="bold white", width=14)
    table.add_column("Candidates", justify="right", style="bold yellow", width=12)
    table.add_column("Probability", justify="right", style="bold green", width=14)
    table.add_column("Distribution", justify="left", ratio=2)

    for outcome in analysis.outcomes:
        exact_pegs = " ".join(["[bold red]●[/]"] * outcome.feedback.exact)
        misplaced_pegs = " ".join(["[bold white]○[/]"] * outcome.feedback.misplaced)
        empty_count = max(0, config.num_pegs - outcome.feedback.exact - outcome.feedback.misplaced)
        empty_pegs = " ".join(["[dim]·[/]"] * empty_count)
        pegs_str = " ".join(filter(bool, [exact_pegs, misplaced_pegs, empty_pegs]))
        if not pegs_str:
            pegs_str = "[dim]·[/dim]"

        bar_len = int(outcome.percentage / 4)
        bar = "█" * bar_len + "░" * (25 - bar_len)
        table.add_row(
            pegs_str,
            str(outcome.feedback.exact),
            str(outcome.feedback.misplaced),
            str(outcome.count),
            f"{outcome.percentage:5.1f}%",
            f"[bright_cyan]{bar}[/bright_cyan]",
        )

    return Panel(
        Group(Text.from_markup(summary), table),
        title="[bold bright_cyan]Guess Information & Partition Distribution Analysis[/bold bright_cyan]",
        box=box.ROUNDED,
        style="bright_cyan",
    )


def render_candidate_inspection(belief_state: BeliefState, config: GameConfig, max_display: int = 18) -> Panel:
    """Render a view of the current candidate space and sample consistent codes."""
    total = belief_state.size
    is_sampled = getattr(belief_state, "is_sampled", False)
    sampled_tag = f" [dim](Sampled pool from ~{belief_state.total_space_size:,} codes)[/dim]" if is_sampled else ""
    entropy_state = math.log2(total) if total > 0 else 0.0

    lines = [
        f"[bold]Remaining Candidate Secrets:[/] [bold yellow]{total:,}[/bold yellow]{sampled_tag}",
        f"[bold]Belief Space Entropy:[/] [bold cyan]{entropy_state:.2f} bits of remaining uncertainty[/bold cyan]",
        "",
        "[bold bright_white]Sample of Consistent Codes:[/bold bright_white]",
    ]

    sample_codes = belief_state.candidates[:max_display]
    grid_rows = []
    chunk_size = 4
    for i in range(0, len(sample_codes), chunk_size):
        chunk = sample_codes[i : i + chunk_size]
        rendered_chunk = [f"#{i + j + 1:02d}: {format_code(c, config)}" for j, c in enumerate(chunk)]
        grid_rows.append("   ".join(rendered_chunk))

    lines.extend(grid_rows)
    if total > max_display:
        lines.append(f"[dim]... and {total - max_display} more consistent candidate codes.[/dim]")

    return Panel(
        Text.from_markup("\n".join(lines)),
        title="[bold bright_green]Candidate State Space Inspection[/bold bright_green]",
        box=box.ROUNDED,
        style="bright_green",
    )


def render_top_guesses_table(top_guesses: Sequence[GuessScore], config: GameConfig) -> Table:
    """Render comparison table of top evaluated candidate guesses."""
    table = Table(
        title="Top Candidate Guesses Ranked by Entropy",
        box=box.ROUNDED,
        header_style="bold bright_cyan",
        expand=True,
    )
    table.add_column("Rank", justify="center", style="bold", width=6)
    table.add_column("Guess Code", justify="center", ratio=2)
    table.add_column("Candidate?", justify="center", width=12)
    table.add_column("Entropy (bits)", justify="right", style="bold cyan", width=14)
    table.add_column("Worst-Case", justify="right", style="bold red", width=12)
    table.add_column("Exp Remaining", justify="right", style="bold magenta", width=15)
    table.add_column("Partitions", justify="right", style="bold yellow", width=12)

    for rank, g in enumerate(top_guesses, 1):
        cand_str = "[bold green]Yes[/]" if g.is_candidate else "[dim]No[/]"
        table.add_row(
            f"#{rank}",
            format_code(g.guess, config),
            cand_str,
            f"{g.entropy_bits:.4f}",
            str(g.worst_case_remaining),
            f"{g.expected_remaining:.2f}",
            str(g.partition_count),
        )

    return table


def render_interactive_help() -> Panel:
    """Render interactive command cheatsheet."""
    help_text = (
        "[bold bright_cyan]Available Commands During Play:[/bold bright_cyan]\n"
        "  [bold yellow]<guess>[/bold yellow]          Submit your guess (e.g. [bold]0 1 2 3[/bold] or [bold]R G B Y[/bold])\n"
        "  [bold yellow]hint[/bold yellow] / [bold yellow]h[/bold yellow]        Request an optimal AI tactical hint for this turn\n"
        "  [bold yellow]eval <guess>[/bold yellow]    Inspect score, Shannon entropy, and feedback frequency table for any guess\n"
        "  [bold yellow]top [N][/bold yellow]         Evaluate and rank top candidate guesses by entropy (e.g. [bold]top 5[/bold])\n"
        "  [bold yellow]inspect[/bold yellow] / [bold yellow]state[/bold yellow]  Inspect remaining candidate secret space and consistent codes\n"
        "  [bold yellow]timeline <sec>[/bold yellow] Set AI search timeline deadline in seconds (e.g. [bold]timeline 1.5[/bold])\n"
        "  [bold yellow]board[/bold yellow]           Redraw game board table\n"
        "  [bold yellow]?[/bold yellow] / [bold yellow]legend[/bold yellow]       Show color palette legend\n"
        "  [bold yellow]quit[/bold yellow] / [bold yellow]exit[/bold yellow]     Abort current game"
    )
    return Panel(Text.from_markup(help_text), title="[bold bright_white]Command Help[/bold bright_white]", box=box.ROUNDED, style="bright_blue")
