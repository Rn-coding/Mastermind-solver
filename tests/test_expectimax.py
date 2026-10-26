"""Tests for BoundedExpectimaxSolver."""

from mastermind.config import GameConfig
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.budget import SearchBudget
from mastermind.solver.expectimax import BoundedExpectimaxSolver


class TestBoundedExpectimaxSolver:
    def test_single_candidate(self):
        config = GameConfig(num_pegs=3, num_colors=3)
        bs = BeliefState(config, initial_candidates=[(0, 1, 2)])
        solver = BoundedExpectimaxSolver(config)
        res = solver.solve(bs)

        assert res.guess == (0, 1, 2)
        assert res.telemetry.is_exact is True
        assert res.telemetry.best_score == 1.0

    def test_expectimax_depth_1(self):
        config = GameConfig(num_pegs=3, num_colors=3)
        bs = BeliefState(config)
        solver = BoundedExpectimaxSolver(config, max_depth=1)
        res = solver.solve(bs)

        assert res.guess is not None
        assert res.telemetry.nodes_evaluated > 0
        assert res.telemetry.best_score > 0

    def test_expectimax_depth_2_small_board(self):
        config = GameConfig(num_pegs=2, num_colors=3)
        bs = BeliefState(config)
        solver = BoundedExpectimaxSolver(config, max_depth=2)
        res = solver.solve(bs)

        assert res.guess is not None
        assert res.telemetry.max_depth_reached == 2
        assert res.telemetry.best_score > 0

    def test_expectimax_with_tight_budget(self):
        config = GameConfig(num_pegs=3, num_colors=4)
        bs = BeliefState(config)
        budget = SearchBudget(max_nodes=3)
        solver = BoundedExpectimaxSolver(config, budget=budget, max_depth=2)
        res = solver.solve(bs)

        assert res.guess is not None
        assert res.telemetry.is_budget_exhausted is True
