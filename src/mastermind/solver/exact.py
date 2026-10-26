"""Exact policy search computing provably optimal decision trees for small configurations."""

from __future__ import annotations
from enum import Enum
import math
import time
from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback
from mastermind.rules import calculate_feedback, generate_all_codes
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.candidates import CandidateGenerator, GuessFilterPolicy
from mastermind.telemetry import GuessScore, SearchTelemetry, SolverResult


class ExactObjective(str, Enum):
    """Optimization objectives for exact game-tree policy search."""

    EXPECTED_TOTAL_GUESSES = "expected_total_guesses"
    WORST_CASE_GUESSES = "worst_case_guesses"


class ExactSearchLimitExceeded(RuntimeError):
    """Raised when the exact search exceeds the allowed computational budget."""
    pass


class ExactPolicySolver:
    """Computes globally optimal decision policies via exhaustive game-tree search."""

    def __init__(
        self,
        config: GameConfig,
        objective: ExactObjective = ExactObjective.EXPECTED_TOTAL_GUESSES,
        max_states: int = 50000,
        filter_policy: GuessFilterPolicy = GuessFilterPolicy.ALL_LEGAL_CODES,
    ) -> None:
        self._config = config
        self._objective = objective
        self._max_states = max_states
        self._filter_policy = filter_policy

        self._all_codes = tuple(generate_all_codes(config))
        self._cand_gen = CandidateGenerator(config)

        # Transposition table: frozenset(candidates) -> (optimal_cost, best_guess)
        self._memo: Dict[FrozenSet[Code], Tuple[float, Code]] = {}
        self._states_evaluated = 0

    @property
    def objective(self) -> ExactObjective:
        return self._objective

    def is_tractable_for_exact_search(self, candidate_count: int) -> bool:
        """Heuristic check whether the current belief state is within exact search reach."""
        # For small search spaces (|C| <= 64 or config total <= 100), full exact search completes rapidly
        return candidate_count <= 81 or len(self._all_codes) <= 100

    def solve(
        self,
        belief_state: BeliefState,
        max_time_seconds: Optional[float] = None,
    ) -> SolverResult:
        """Find the provably optimal guess minimizing expected or worst-case total guesses.

        Args:
            belief_state: Current candidate secret possibilities.
            max_time_seconds: Optional timeout in seconds.

        Returns:
            SolverResult with optimal guess and full exact search telemetry.
        """
        start_time = time.perf_counter()
        deadline = start_time + max_time_seconds if max_time_seconds else None

        self._states_evaluated = 0
        self._memo.clear()

        # Generate guess space
        guesses = self._cand_gen.generate_candidate_guesses(
            belief_state, policy=self._filter_policy
        )

        initial_candidates = frozenset(belief_state.candidates)
        cost, best_guess = self._search(initial_candidates, guesses, deadline)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        telemetry = SearchTelemetry(
            method_name=f"Exact Tree Search ({self._objective.value})",
            objective=self._objective.value,
            initial_candidates_count=len(initial_candidates),
            guesses_considered_count=len(guesses),
            nodes_evaluated=self._states_evaluated,
            max_depth_reached=math.ceil(cost),
            elapsed_time_ms=elapsed_ms,
            is_exact=True,
            is_budget_exhausted=False,
            stopping_reason="Provably optimal exact policy found",
            best_score=cost,
            top_guesses=(
                GuessScore(
                    guess=best_guess,
                    score=cost,
                    is_candidate=best_guess in initial_candidates,
                    worst_case_remaining=0,
                    expected_remaining=0.0,
                    entropy_bits=0.0,
                    partition_count=1,
                ),
            ),
        )

        return SolverResult(guess=best_guess, telemetry=telemetry)

    def _search(
        self,
        candidates: FrozenSet[Code],
        guess_pool: Sequence[Code],
        deadline: Optional[float],
    ) -> Tuple[float, Code]:
        """Recursive helper with memoization computing optimal remaining cost."""
        if len(candidates) == 0:
            return 0.0, guess_pool[0]

        # Base Case 1: Exactly 1 candidate remaining -> Guess it directly
        if len(candidates) == 1:
            only = next(iter(candidates))
            return 1.0, only

        # Base Case 2: Exactly 2 candidates remaining -> Guess either one
        if len(candidates) == 2:
            first = next(iter(candidates))
            if self._objective == ExactObjective.EXPECTED_TOTAL_GUESSES:
                # With p=0.5 it's correct (1 turn), with p=0.5 it's incorrect (2 turns) -> E = 1.5 turns
                return 1.5, first
            else:
                # Worst case is 2 turns
                return 2.0, first

        # Check memo table
        if candidates in self._memo:
            return self._memo[candidates]

        # Resource limits check
        self._states_evaluated += 1
        if self._states_evaluated > self._max_states:
            raise ExactSearchLimitExceeded(
                f"Exact search exceeded state expansion budget of {self._max_states} states."
            )
        if deadline and time.perf_counter() >= deadline:
            raise ExactSearchLimitExceeded("Exact search exceeded time budget.")

        best_cost = float("inf")
        best_guess = guess_pool[0]
        n_cands = len(candidates)

        # For exact search, prioritize remaining candidates first to find quick cutoffs
        ordered_guesses = sorted(guess_pool, key=lambda g: g not in candidates)

        for guess in ordered_guesses:
            # Partition candidates by feedback
            partitions: Dict[Feedback, List[Code]] = {}
            for cand in candidates:
                fb = calculate_feedback(cand, guess)
                if fb not in partitions:
                    partitions[fb] = []
                partitions[fb].append(cand)

            # A guess that leaves all candidates in a single partition provides zero information
            # and cannot make progress (would cause infinite loop).
            if any(len(branch) == n_cands for branch in partitions.values()):
                continue

            is_in_candidates = guess in candidates
            total_branch_cost = 0.0
            worst_branch_cost = 0.0

            for fb, branch_cands in partitions.items():
                if fb.is_solved(self._config.num_pegs):
                    # Guess was the secret! Cost for this branch is 1 (the current guess)
                    branch_cost = 1.0
                else:
                    sub_cost, _ = self._search(frozenset(branch_cands), guess_pool, deadline)
                    branch_cost = 1.0 + sub_cost

                total_branch_cost += (len(branch_cands) / n_cands) * branch_cost
                worst_branch_cost = max(worst_branch_cost, branch_cost)

            current_cost = (
                total_branch_cost
                if self._objective == ExactObjective.EXPECTED_TOTAL_GUESSES
                else worst_branch_cost
            )

            # Tie-breaking: prefer guess in candidates
            if current_cost < best_cost or (
                math.isclose(current_cost, best_cost, rel_tol=1e-9)
                and is_in_candidates
                and best_guess not in candidates
            ):
                best_cost = current_cost
                best_guess = guess

        self._memo[candidates] = (best_cost, best_guess)
        return best_cost, best_guess
