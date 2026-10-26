"""Tests for the Mastermind environment and observation boundaries."""

import pytest
from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
from mastermind.setters.fixed import KnownFixedSetter


class TestMastermindEnvironment:
    def test_environment_initialization(self):
        config = GameConfig(num_pegs=4, num_colors=6, max_guesses=5)
        env = MastermindEnvironment(config=config)
        obs = env.get_observation()

        assert obs.turn_number == 0
        assert len(obs.history) == 0
        assert obs.is_terminal is False
        assert obs.is_solved is False
        assert obs.remaining_guesses == 5

    def test_submit_guess_progression(self):
        config = GameConfig(num_pegs=4, num_colors=6, max_guesses=5)
        setter = KnownFixedSetter(secret=(0, 1, 2, 3), config=config)
        env = MastermindEnvironment(config=config, setter=setter)

        res1 = env.submit_guess((0, 1, 4, 5))
        assert res1.turn == 1
        assert res1.feedback.exact == 2
        assert res1.feedback.misplaced == 0
        assert res1.is_terminal is False
        assert res1.is_solved is False

        obs1 = env.get_observation()
        assert obs1.turn_number == 1
        assert len(obs1.history) == 1
        assert obs1.remaining_guesses == 4
        assert obs1.last_guess == (0, 1, 4, 5)

    def test_solving_terminates_game(self):
        config = GameConfig(num_pegs=4, num_colors=6, max_guesses=10)
        setter = KnownFixedSetter(secret=(0, 1, 2, 3), config=config)
        env = MastermindEnvironment(config=config, setter=setter)

        res = env.submit_guess((0, 1, 2, 3))
        assert res.is_solved is True
        assert res.is_terminal is True
        assert res.feedback.exact == 4

        obs = env.get_observation()
        assert obs.is_solved is True
        assert obs.is_terminal is True

    def test_max_guesses_terminates_game_as_unsolved(self):
        config = GameConfig(num_pegs=4, num_colors=6, max_guesses=2)
        setter = KnownFixedSetter(secret=(0, 1, 2, 3), config=config)
        env = MastermindEnvironment(config=config, setter=setter)

        env.submit_guess((5, 5, 5, 5))
        res2 = env.submit_guess((4, 4, 4, 4))

        assert res2.turn == 2
        assert res2.is_terminal is True
        assert res2.is_solved is False

        # Attempting to guess after terminal raises error
        with pytest.raises(RuntimeError, match="terminal state"):
            env.submit_guess((0, 1, 2, 3))

    def test_invalid_guess_rejected(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        env = MastermindEnvironment(config=config)

        with pytest.raises(ValueError):
            env.submit_guess((0, 1, 2))  # too short

        with pytest.raises(ValueError):
            env.submit_guess((0, 1, 2, 99))  # color out of range

        # Ensure turn didn't increment on failed validation
        assert env.turn_number == 0

    def test_secret_encapsulation_boundary(self):
        config = GameConfig(num_pegs=4, num_colors=6, max_guesses=5)
        setter = KnownFixedSetter(secret=(1, 2, 3, 4), config=config)
        env = MastermindEnvironment(config=config, setter=setter)

        obs = env.get_observation()
        # Verify Observation contains no secret attributes
        assert not hasattr(obs, "secret")
        assert not hasattr(obs, "_secret")
        assert not hasattr(obs, "setter")

        # Calling reveal_secret while in progress should raise PermissionError
        with pytest.raises(PermissionError, match="in progress"):
            env.reveal_secret()

        # Once terminal, reveal_secret succeeds
        env.submit_guess((1, 2, 3, 4))
        assert env.is_terminal is True
        assert env.reveal_secret() == (1, 2, 3, 4)

    def test_environment_reset(self):
        config = GameConfig(num_pegs=3, num_colors=4, max_guesses=3)
        setter1 = KnownFixedSetter(secret=(0, 1, 2), config=config)
        env = MastermindEnvironment(config=config, setter=setter1)

        env.submit_guess((0, 1, 3))
        assert env.turn_number == 1

        setter2 = KnownFixedSetter(secret=(2, 1, 0), config=config)
        obs = env.reset(setter=setter2)

        assert obs.turn_number == 0
        assert len(obs.history) == 0
        assert obs.is_terminal is False

        res = env.submit_guess((2, 1, 0))
        assert res.is_solved is True
