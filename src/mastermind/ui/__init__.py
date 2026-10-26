"""User interface modules for Mastermind."""

from mastermind.ui.app import MastermindApp, main
from mastermind.ui.formatters import format_code, format_feedback, format_peg, parse_guess_input
from mastermind.ui.game_view import (
    render_board,
    render_color_legend,
    render_header,
    render_status,
    render_telemetry_panel,
)

__all__ = [
    "MastermindApp",
    "main",
    "format_code",
    "format_feedback",
    "format_peg",
    "parse_guess_input",
    "render_board",
    "render_color_legend",
    "render_header",
    "render_status",
    "render_telemetry_panel",
]
