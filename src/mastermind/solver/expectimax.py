"""Bounded Expectimax search optimizing expected remaining cost with frontier heuristics."""

from __future__ import annotations
import math
import time
from typing import Dict, List, Optional, Sequence, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback
from mastermind.rules import calculate_feedback
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.budget import SearchBudget
from mastermind.solver.candidates import CandidateGenerator, GuessFilterPolicy
from mastermind.telemetry import GuessScore, SearchTelemetry, SolverResult


class BoundedExpectimaxSolver:
    """Multi-ply lookahead Expectimax solver with frontier heuristic evaluation."""

    def __init__(
        self,
        config: GameConfig,
        budget: Optional[SearchBudget] = None,
        max_depth: int = 2,
        filter_policy: GuessFilterPolicy = GuessFilterPolicy.ALL_LEGAL_CODES,
    ) -> None:
        self._config = config
        self._budget = budget or SearchBudget(max_depth=max_depth)
        self._max_depth = max_depth
        self._filter_policy = filter_policy
        self._cand_gen = CandidateGenerator(config)

    def _frontier_heuristic(self, candidate_count: int) -> float:
        """Estimate expected remaining turns from a belief state of given size at search frontier."""
        if candidate_count <= 1:
            return 1.0
        if candidate_count == 2:
            return 1.5
        # Entropy-based turn estimate: each turn in Mastermind typically yields ~1.8 - 2.5 bits of information
        bits = math.log2(candidate_count)
        estimated_turns = 1.0 + (bits / 2.0)
        return estimated_turns

    def solve(
        self,
        belief_state: BeliefState,
        candidate_guesses: Optional[Sequence[Code]] = None,
    ) -> SolverResult:
        """Execute bounded expectimax search to find the guess minimizing expected cost."""
        self._budget.reset()

        if belief_state.size == 1:
            only = belief_state.candidates[0]
            g_score = GuessScore(only, 1.0, True, 0, 0.0, 0.0, 1)
            telemetry = SearchTelemetry(
                method_name="Bounded Expectimax",
                objective="minimize_expected_total_guesses",
                initial_candidates_count=1,
                guesses_considered_count=1,
                nodes_evaluated=1,
                max_depth_reached=1,
                elapsed_time_ms=self._budget.elapsed_ms,
                is_exact=True,
                is_budget_exhausted=False,
                stopping_reason="Single remaining candidate",
                best_score=1.0,
                top_guesses=(g_score,),
            )
            return SolverResult(guess=only, telemetry=telemetry)

        guesses_to_eval = candidate_guesses or self._cand_gen.generate_candidate_guesses(
            belief_state,
            policy=self._filter_policy,
            max_guesses=self._budget.max_candidate_guesses,
        )

        best_cost = float("inf")
        best_guess = guesses_to_eval[0]
        evaluated_scores: List[GuessScore] = []

        for idx, guess in enumerate(guesses_to_eval):
            if not self._budget.tick_node():
                break

            partitions = belief_state.partition(guess)
            is_cand = belief_state.contains(guess)
            n_cands = belief_state.size

            # Evaluate immediate partition statistics
            worst_case = max(len(p) for p in partitions.values()) if partitions else 0
            exp_rem = sum(len(p) ** 2 for p in partitions.values()) / n_cands if n_cands else 0.0

            # Calculate expected cost across branches
            branch_expected_cost = 0.0
            for fb, branch_cands in partitions.items():
                if fb.is_solved(self._config.num_pegs):
                    branch_cost = 1.0
                elif self._max_depth <= 1:
                    branch_cost = 1.0 + self._frontier_heuristic(len(branch_cands))
                else:
                    # Recursive lookahead to depth - 1
                    sub_cost = self._expectimax_recursive(branch_cands, current_depth=2)
                    branch_cost = 1.0 + sub_cost

                p_fb = len(branch_cands) / n_cands
                branch_expected_cost += p_fb * branch_cost

            score_item = GuessScore(
                guess=guess,
                score=branch_expected_cost,
                is_candidate=is_cand,
                worst_case_remaining=worst_case,
                expected_remaining=exp_rem,
                entropy_bits=0.0,
                partition_count=len(partitions),
            )
            evaluated_scores.append(score_item)

            # Tie breaking: prefer lower expected cost, then candidate secret
            is_better = False
            if branch_expected_cost < best_cost:
                is_better = True
            elif math.isclose(branch_expected_cost, best_cost, rel_tol=1e-9):
                if is_cand and not (best_guess in set(belief_state.candidates)):
                    is_better = True

            if is_better:
                best_cost = branch_expected_cost
                best_guess = guess

        evaluated_scores.sort(key=lambda x: (x.score, not x.is_candidate))
        top_5 = tuple(evaluated_scores[:5])

        stopping_reason = (
            self._budget.exhaustion_reason
            if self._budget.is_exhausted
            else f"Completed expectimax search to depth {self._max_depth}"
        )

        telemetry = SearchTelemetry(
            method_name=f"Bounded Expectimax (Depth {self._max_depth})",
            objective="minimize_expected_total_guesses",
            initial_candidates_count=belief_state.size,
            guesses_considered_count=len(guesses_to_eval),
            nodes_evaluated=self._budget.nodes_evaluated,
            max_depth_reached=self._max_depth,
            elapsed_time_ms=self._budget.elapsed_ms,
            is_exact=False,
            is_budget_exhausted=self._budget.is_exhausted,
            stopping_reason=stopping_reason,
            best_score=best_cost,
            top_guesses=top_5,
        )

        return SolverResult(guess=best_guess, telemetry=telemetry)

    def _expectimax_recursive(self, candidates: List[Code], current_depth: int) -> float:
        """Recursive helper evaluating child chance nodes and optimal choice."""
        if len(candidates) <= 2 or current_depth >= self._max_depth:
            return self._frontier_heuristic(len(candidates))

        if not self._budget.tick_node():
            return self._frontier_heuristic(len(candidates))

        # Sample a fast subset of candidate guesses for deeper lookahead
        sub_guesses = candidates[:min(len(candidates), 12)]
        best_val = float("inf")
        n_cands = len(candidates)

        for g in sub_guesses:
            # Partition branch
            parts: Dict[Feedback, int] = {}
            for c in candidates:
                fb = calculate_feedback(c, g)
                parts[fb] = parts.get(fb, 0) + 1

            exp_val = 0.0
            for fb, count in parts.items():
                if fb.is_solved(self._config.num_pegs):
                    cost = 1.0
                else:
                    cost = 1.0 + self._frontier_heuristic(count)
                exp_val += (count / n_cands) * cost

            if exp_val < best_val:
                best_val = exp_val

        return best_val
