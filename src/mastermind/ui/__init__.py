"""User interface modules for Mastermind."""

from mastermind.ui.app import MastermindApp, main
from mastermind.ui.formatters import format_code, format_feedback, format_peg, parse_guess_input
from mastermind.ui.game_view import (
    render_ai_hint,
    render_board,
    render_candidate_inspection,
    render_color_legend,
    render_detailed_guess_eval,
    render_header,
    render_interactive_help,
    render_status,
    render_telemetry_panel,
    render_top_guesses_table,
)

__all__ = [
    "MastermindApp",
    "main",
    "format_code",
    "format_feedback",
    "format_peg",
    "parse_guess_input",
    "render_ai_hint",
    "render_board",
    "render_candidate_inspection",
    "render_color_legend",
    "render_detailed_guess_eval",
    "render_header",
    "render_interactive_help",
    "render_status",
    "render_telemetry_panel",
    "render_top_guesses_table",
]
