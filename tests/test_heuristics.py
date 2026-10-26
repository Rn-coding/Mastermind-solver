"""Tests for 1-ply heuristic solvers."""

import pytest
from mastermind.config import GameConfig
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.heuristic import (
    EntropyHeuristic,
    ExpectedSizeHeuristic,
    KnuthMinimaxHeuristic,
    PartitionHeuristic,
)


class TestHeuristics:
    @pytest.fixture
    def small_belief_state(self):
        config = GameConfig(num_pegs=3, num_colors=3, allow_repeats=True)
        return BeliefState(config)

    def test_knuth_minimax_evaluates(self, small_belief_state):
        h = KnuthMinimaxHeuristic()
        res = h.select_best_guess(small_belief_state.candidates, small_belief_state)
        assert res.guess is not None
        assert res.telemetry.method_name == "Knuth Minimax (Worst-Case)"
        assert res.telemetry.nodes_evaluated == len(small_belief_state.candidates)
        assert res.telemetry.best_score > 0

    def test_entropy_heuristic_evaluates(self, small_belief_state):
        h = EntropyHeuristic()
        res = h.select_best_guess(small_belief_state.candidates, small_belief_state)
        assert res.guess is not None
        assert res.telemetry.method_name == "Shannon Entropy (Information Gain)"
        # Score is negative entropy, so best score <= 0
        assert res.telemetry.best_score <= 0

    def test_expected_size_heuristic(self, small_belief_state):
        h = ExpectedSizeHeuristic()
        res = h.select_best_guess(small_belief_state.candidates, small_belief_state)
        assert res.guess is not None
        assert res.telemetry.best_score > 0

    def test_single_candidate_short_circuit(self):
        config = GameConfig(num_pegs=3, num_colors=3)
        bs = BeliefState(config, initial_candidates=[(0, 1, 2)])
        h = EntropyHeuristic()
        res = h.select_best_guess([(0, 0, 0), (0, 1, 2)], bs)
        assert res.guess == (0, 1, 2)
        assert res.telemetry.is_exact is True
