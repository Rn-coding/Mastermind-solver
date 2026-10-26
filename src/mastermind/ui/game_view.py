"""Modern terminal game view rendering board states, history, and status banners."""

from __future__ import annotations
from typing import Optional
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group
from rich import box

from mastermind.config import GameConfig
from mastermind.observation import Code, Observation
from mastermind.telemetry import SearchTelemetry
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
