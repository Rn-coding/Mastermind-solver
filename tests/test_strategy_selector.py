"""Tests for dynamic StrategySelector and adaptive AI player."""

from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
from mastermind.players.ai import AIPlayer
from mastermind.setters.fixed import KnownFixedSetter
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.strategy_selector import StrategySelector


class TestStrategySelector:
    def test_profiling_small_recommends_exact(self):
        # 2 pegs, 3 colors = 9 codes
        config = GameConfig(num_pegs=2, num_colors=3)
        bs = BeliefState(config)
        selector = StrategySelector(config)
        profile = selector.profile_workload(bs)

        assert "Exact" in profile.recommended_strategy
        assert profile.candidate_count == 9

    def test_profiling_medium_recommends_expectimax(self):
        # 3 pegs, 4 colors = 64 codes
        config = GameConfig(num_pegs=3, num_colors=4)
        bs = BeliefState(config)
        selector = StrategySelector(config)
        profile = selector.profile_workload(bs)

        assert "Expectimax" in profile.recommended_strategy

    def test_profiling_standard_recommends_entropy(self):
        # 4 pegs, 6 colors = 1296 codes
        config = GameConfig(num_pegs=4, num_colors=6)
        bs = BeliefState(config)
        selector = StrategySelector(config)
        profile = selector.profile_workload(bs)

        assert "Entropy" in profile.recommended_strategy

    def test_profiling_large_recommends_sampled(self):
        # 5 pegs, 8 colors = 32,768 codes
        config = GameConfig(num_pegs=5, num_colors=8)
        bs = BeliefState(config, initial_candidates=[(0,) * 5] * 5000)
        selector = StrategySelector(config)
        profile = selector.profile_workload(bs)

        assert "Sampled" in profile.recommended_strategy

    def test_adaptive_ai_player_solves_game(self):
        config = GameConfig(num_pegs=3, num_colors=4, allow_repeats=True, max_guesses=8)
        secret = (3, 1, 0)
        setter = KnownFixedSetter(secret=secret, config=config)
        env = MastermindEnvironment(config=config, setter=setter)

        ai = AIPlayer(use_strategy_selector=True)
        obs = env.get_observation()

        while not obs.is_terminal:
            guess = ai.choose_guess(obs)
            env.submit_guess(guess)
            obs = env.get_observation()

        assert obs.is_solved is True
        assert env.reveal_secret() == secret
