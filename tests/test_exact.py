"""Tests for ExactPolicySolver computing optimal decision trees."""

import pytest
from mastermind.config import GameConfig
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.candidates import GuessFilterPolicy
from mastermind.solver.exact import ExactObjective, ExactPolicySolver, ExactSearchLimitExceeded


class TestExactPolicySolver:
    def test_single_candidate_exact(self):
        config = GameConfig(num_pegs=2, num_colors=3)
        bs = BeliefState(config, initial_candidates=[(0, 1)])
        solver = ExactPolicySolver(config)
        res = solver.solve(bs)

        assert res.guess == (0, 1)
        assert res.telemetry.is_exact is True
        assert res.telemetry.best_score == 1.0

    def test_two_candidates_exact(self):
        config = GameConfig(num_pegs=2, num_colors=3)
        bs = BeliefState(config, initial_candidates=[(0, 1), (1, 2)])
        solver = ExactPolicySolver(config, objective=ExactObjective.EXPECTED_TOTAL_GUESSES)
        res = solver.solve(bs)

        assert res.guess in bs.candidates
        assert res.telemetry.is_exact is True
        # E = 0.5 * 1 + 0.5 * 2 = 1.5
        assert res.telemetry.best_score == 1.5

    def test_small_board_exact_expected_guesses(self):
        # 2 pegs, 3 colors = 9 codes
        config = GameConfig(num_pegs=2, num_colors=3, allow_repeats=True)
        bs = BeliefState(config)
        solver = ExactPolicySolver(
            config,
            objective=ExactObjective.EXPECTED_TOTAL_GUESSES,
            filter_policy=GuessFilterPolicy.ALL_LEGAL_CODES,
        )
        res = solver.solve(bs)

        assert res.guess is not None
        assert res.telemetry.is_exact is True
        assert res.telemetry.nodes_evaluated > 0
        # Optimal expected turns on 2-peg 3-color Mastermind is <= 2.5
        assert 1.0 < res.telemetry.best_score <= 2.8

    def test_small_board_exact_worst_case_guesses(self):
        config = GameConfig(num_pegs=2, num_colors=3, allow_repeats=True)
        bs = BeliefState(config)
        solver = ExactPolicySolver(
            config,
            objective=ExactObjective.WORST_CASE_GUESSES,
            filter_policy=GuessFilterPolicy.CANDIDATES_ONLY,
        )
        res = solver.solve(bs)

        assert res.guess is not None
        assert res.telemetry.is_exact is True
        assert res.telemetry.best_score in (2.0, 3.0)

    def test_exact_search_limit_exceeded(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        bs = BeliefState(config)
        # Low limit to trigger budget exception
        solver = ExactPolicySolver(config, max_states=10)
        with pytest.raises(ExactSearchLimitExceeded):
            solver.solve(bs)
