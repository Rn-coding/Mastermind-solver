"""Tests for modern terminal UI formatters, parsing, and rendering."""

import pytest
from rich.console import Console

from mastermind.config import GameConfig
from mastermind.observation import Feedback, Observation, TurnRecord
from mastermind.ui.formatters import (
    format_code,
    format_feedback,
    format_peg,
    get_color_theme,
    parse_guess_input,
)
from mastermind.ui.game_view import render_board, render_color_legend, render_header, render_status


class TestUIFormatters:
    def test_get_color_theme(self):
        theme0 = get_color_theme(0)
        assert theme0.name == "Red"
        assert theme0.letter == "R"

        theme1 = get_color_theme(1)
        assert theme1.name == "Green"
        assert theme1.letter == "G"

    def test_format_peg(self):
        text = format_peg(0, show_label=True)
        assert "Red" in text
        assert "0" in text

        compact = format_peg(0, show_label=False)
        assert "●" in compact

    def test_format_code(self):
        code = (0, 1, 2)
        formatted = format_code(code)
        assert "R" in formatted
        assert "G" in formatted
        assert "B" in formatted

    def test_format_feedback(self):
        fb = Feedback(exact=2, misplaced=1)
        res = format_feedback(fb, num_pegs=4)
        assert "Exact: 2" in res
        assert "Misplaced: 1" in res


class TestInputParser:
    def test_space_separated_integers(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        guess = parse_guess_input("0 1 2 3", config)
        assert guess == (0, 1, 2, 3)

    def test_comma_separated_integers(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        guess = parse_guess_input("0, 1, 2, 3", config)
        assert guess == (0, 1, 2, 3)

    def test_compact_integers(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        guess = parse_guess_input("0123", config)
        assert guess == (0, 1, 2, 3)

    def test_letter_tokens_space_separated(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        guess = parse_guess_input("R G B Y", config)
        assert guess == (0, 1, 2, 3)

    def test_letter_tokens_compact(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        guess = parse_guess_input("RGBY", config)
        assert guess == (0, 1, 2, 3)

    def test_case_insensitivity(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        guess = parse_guess_input("r g b y", config)
        assert guess == (0, 1, 2, 3)

    def test_parse_empty_raises(self):
        config = GameConfig()
        with pytest.raises(ValueError, match="Input cannot be empty"):
            parse_guess_input("   ", config)

    def test_wrong_peg_count_raises(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        with pytest.raises(ValueError, match="Expected 4 pegs"):
            parse_guess_input("0 1 2", config)

    def test_out_of_bounds_color_raises(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        with pytest.raises(ValueError, match="out of bounds"):
            parse_guess_input("0 1 2 9", config)

    def test_unrecognized_token_raises(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        with pytest.raises(ValueError, match="Unrecognized color token"):
            parse_guess_input("R G X Y", config)

    def test_repeats_prohibited_raises(self):
        config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=False)
        with pytest.raises(ValueError, match="Duplicate colors are not permitted"):
            parse_guess_input("0 0 1 2", config)


class TestGameViewRendering:
    def test_render_header(self):
        config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=True, max_guesses=10)
        panel = render_header(config)
        console = Console(record=True, width=80)
        console.print(panel)
        output = console.export_text()
        assert "MASTERMIND AI" in output
        assert "Pegs: 4" in output
        assert "Colors: 6" in output

    def test_render_color_legend(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        panel = render_color_legend(config)
        console = Console(record=True, width=120)
        console.print(panel)
        output = console.export_text()
        assert "Available Colors" in output
        assert "Red" in output
        assert "Green" in output

    def test_render_board(self):
        config = GameConfig(num_pegs=4, num_colors=6, max_guesses=3)
        obs = Observation(
            config=config,
            history=(
                TurnRecord(turn=1, guess=(0, 1, 2, 3), feedback=Feedback(1, 1)),
            ),
            turn_number=1,
            is_terminal=False,
            is_solved=False,
        )
        table = render_board(obs)
        console = Console(record=True, width=100)
        console.print(table)
        output = console.export_text()
        assert "Game Board" in output
        assert "Exact" in output
        assert "Misplaced" in output

    def test_render_status(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        # In progress
        obs_progress = Observation(config, (), 0, False, False)
        panel = render_status(obs_progress)
        assert panel is not None

        # Solved
        obs_solved = Observation(config, (), 3, True, True)
        panel_solved = render_status(obs_solved, secret=(0, 1, 2, 3))
        console = Console(record=True, width=80)
        console.print(panel_solved)
        output = console.export_text()
        assert "VICTORY" in output

        # Lost
        obs_lost = Observation(config, (), 10, True, False)
        panel_lost = render_status(obs_lost, secret=(0, 1, 2, 3))
        console.print(panel_lost)
        output = console.export_text()
        assert "GAME OVER" in output
