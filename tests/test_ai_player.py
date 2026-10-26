"""Tests for AIPlayer solving complete games."""

from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
from mastermind.players.ai import AIPlayer
from mastermind.setters.fixed import KnownFixedSetter


class TestAIPlayer:
    def test_ai_player_solves_small_game(self):
        config = GameConfig(num_pegs=3, num_colors=4, allow_repeats=True, max_guesses=8)
        secret = (1, 3, 2)
        setter = KnownFixedSetter(secret=secret, config=config)
        env = MastermindEnvironment(config=config, setter=setter)

        ai = AIPlayer()
        obs = env.get_observation()

        while not obs.is_terminal:
            guess = ai.choose_guess(obs)
            assert ai.last_result is not None
            assert ai.last_result.telemetry.nodes_evaluated > 0
            env.submit_guess(guess)
            obs = env.get_observation()

        assert obs.is_solved is True
        assert obs.turn_number <= 6
        assert env.reveal_secret() == secret

    def test_ai_player_solves_standard_game_reproducible(self):
        config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=True, max_guesses=10)
        secret = (4, 2, 0, 5)
        setter = KnownFixedSetter(secret=secret, config=config)
        env = MastermindEnvironment(config=config, setter=setter)

        ai = AIPlayer()
        obs = env.get_observation()

        while not obs.is_terminal:
            guess = ai.choose_guess(obs)
            env.submit_guess(guess)
            obs = env.get_observation()

        assert obs.is_solved is True
        # Standard Mastermind is consistently solved by entropy heuristic in <= 6 turns
        assert obs.turn_number <= 7
        assert env.reveal_secret() == secret
