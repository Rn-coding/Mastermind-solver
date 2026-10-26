"""Tests for human and base player implementations."""

import pytest
from mastermind.config import GameConfig
from mastermind.observation import Observation
from mastermind.players.human import HumanPlayer


class TestHumanPlayer:
    def test_human_player_with_input_callback(self):
        obs = Observation(
            config=GameConfig(num_pegs=4, num_colors=6),
            history=(),
            turn_number=0,
            is_terminal=False,
            is_solved=False,
        )

        player = HumanPlayer(name="Alice", input_fn=lambda o: (0, 1, 2, 3))
        assert player.get_name() == "Alice"
        guess = player.choose_guess(obs)
        assert guess == (0, 1, 2, 3)

    def test_human_player_unconfigured_input_raises(self):
        obs = Observation(
            config=GameConfig(num_pegs=4, num_colors=6),
            history=(),
            turn_number=0,
            is_terminal=False,
            is_solved=False,
        )
        player = HumanPlayer()
        with pytest.raises(RuntimeError, match="No input provider configured"):
            player.choose_guess(obs)
