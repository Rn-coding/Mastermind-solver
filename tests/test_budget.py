"""Tests for SearchBudget accounting and limits."""

import time
from mastermind.solver.budget import SearchBudget


class TestSearchBudget:
    def test_node_limit_exhaustion(self):
        budget = SearchBudget(max_nodes=5)
        for _ in range(4):
            assert budget.tick_node() is True
        # 5th node reaches limit
        assert budget.tick_node() is False
        assert budget.is_exhausted is True
        assert "Node limit reached" in budget.exhaustion_reason

    def test_time_limit_exhaustion(self):
        budget = SearchBudget(max_time_seconds=0.05)
        time.sleep(0.06)
        assert budget.tick_node() is False
        assert budget.is_exhausted is True
        assert "Time budget elapsed" in budget.exhaustion_reason

    def test_reset_clears_exhaustion(self):
        budget = SearchBudget(max_nodes=2)
        budget.tick_node()
        budget.tick_node()
        assert budget.is_exhausted is True

        budget.reset()
        assert budget.is_exhausted is False
        assert budget.nodes_evaluated == 0
