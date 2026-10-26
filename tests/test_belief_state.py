"""Tests for BeliefState manager and candidate filtering."""

import pytest
from mastermind.config import GameConfig
from mastermind.observation import Feedback, Observation, TurnRecord
from mastermind.rules import calculate_feedback
from mastermind.solver.belief_state import BeliefState, InconsistentHistoryError


class TestBeliefState:
    def test_initial_candidates_count(self):
        config = GameConfig(num_pegs=3, num_colors=4, allow_repeats=True)
        bs = BeliefState(config)
        assert bs.size == 64
        assert bs.is_consistent() is True

    def test_filter_by_turn(self):
        config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=True)
        secret = (0, 1, 2, 3)
        bs = BeliefState(config)
        assert bs.size == 1296

        guess = (0, 1, 4, 5)
        fb = calculate_feedback(secret, guess)  # exact=2, misplaced=0

        new_size = bs.filter_by_turn(guess, fb)
        assert new_size < 1296
        assert bs.contains(secret) is True
        for cand in bs.candidates:
            assert calculate_feedback(cand, guess) == fb

    def test_inconsistent_history_raises(self):
        config = GameConfig(num_pegs=3, num_colors=3)
        bs = BeliefState(config)
        # exact=3 means secret must be (0, 0, 0)
        bs.filter_by_turn((0, 0, 0), Feedback(exact=3, misplaced=0))
        assert bs.size == 1
        assert bs.candidates[0] == (0, 0, 0)

        # Contradictory feedback: claiming (1, 1, 1) also has 3 exact matches
        with pytest.raises(InconsistentHistoryError, match="No candidate codes remain consistent"):
            bs.filter_by_turn((1, 1, 1), Feedback(exact=3, misplaced=0))

    def test_partition_consistency(self):
        config = GameConfig(num_pegs=3, num_colors=4)
        bs = BeliefState(config)
        guess = (0, 1, 2)
        partitions = bs.partition(guess)

        # The sum of all partition sizes must exactly equal the total candidate count
        total_partitioned = sum(len(p) for p in partitions.values())
        assert total_partitioned == bs.size

    def test_update_from_observation(self):
        config = GameConfig(num_pegs=3, num_colors=4, allow_repeats=False)
        secret = (0, 1, 2)
        history = (
            TurnRecord(turn=1, guess=(0, 2, 1), feedback=calculate_feedback(secret, (0, 2, 1))),
            TurnRecord(turn=2, guess=(0, 1, 3), feedback=calculate_feedback(secret, (0, 1, 3))),
        )
        obs = Observation(config, history, 2, False, False)

        bs = BeliefState(config)
        bs.update_from_observation(obs)
        assert bs.contains(secret)
