"""Adaptive strategy selector and workload estimator for diverse board sizes."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code
from mastermind.rules import generate_all_codes
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.budget import SearchBudget
from mastermind.solver.candidates import CandidateGenerator, GuessFilterPolicy
from mastermind.solver.exact import ExactObjective, ExactPolicySolver, ExactSearchLimitExceeded
from mastermind.solver.expectimax import BoundedExpectimaxSolver
from mastermind.solver.heuristic import AnytimeEntropyHeuristic, EntropyHeuristic, KnuthMinimaxHeuristic
from mastermind.telemetry import GuessScore, SearchTelemetry, SolverResult


@dataclass(frozen=True)
class WorkloadProfile:
    """Estimated computational complexity of the current belief state."""

    candidate_count: int
    total_code_space: int
    estimated_evaluations: int
    recommended_strategy: str
    rationale: str


class StrategySelector:
    """Dynamically selects optimal search and heuristic algorithms based on workload and budgets."""

    def __init__(self, config: GameConfig, budget: Optional[SearchBudget] = None) -> None:
        self._config = config
        self._budget = budget or SearchBudget()
        self._total_codes = len(generate_all_codes(config))
        self._cand_gen = CandidateGenerator(config)

    def profile_workload(self, belief_state: BeliefState) -> WorkloadProfile:
        """Estimate search effort and determine the most effective algorithmic strategy."""
        cands = belief_state.size
        # Workload is proportional to |Candidates| * |Candidate Guesses|
        est_evals = cands * min(self._total_codes, self._budget.max_candidate_guesses or self._total_codes)

        if cands <= 2:
            return WorkloadProfile(
                candidate_count=cands,
                total_code_space=self._total_codes,
                estimated_evaluations=cands,
                recommended_strategy="Terminal Deduction",
                rationale="Candidate count <= 2: immediate deterministic choice.",
            )
        elif cands <= 36 and est_evals <= 15000:
            return WorkloadProfile(
                candidate_count=cands,
                total_code_space=self._total_codes,
                estimated_evaluations=est_evals,
                recommended_strategy="Exact Tree Policy Search",
                rationale="Small candidate space: full exact tree search guarantees global optimality.",
            )
        elif cands <= 200 and (self._budget.max_depth or 1) >= 2 and est_evals <= 60000:
            return WorkloadProfile(
                candidate_count=cands,
                total_code_space=self._total_codes,
                estimated_evaluations=est_evals,
                recommended_strategy="Bounded Expectimax (Lookahead)",
                rationale="Moderate candidate count: 2-ply expectimax evaluates expected remaining cost.",
            )
        elif cands <= 2500:
            return WorkloadProfile(
                candidate_count=cands,
                total_code_space=self._total_codes,
                estimated_evaluations=est_evals,
                recommended_strategy="Shannon Entropy Partition Heuristic",
                rationale="Standard board size: 1-ply information-gain partition evaluation.",
            )
        else:
            return WorkloadProfile(
                candidate_count=cands,
                total_code_space=self._total_codes,
                estimated_evaluations=est_evals,
                recommended_strategy="Hybrid Sampled Constraint Heuristic",
                rationale="Large board size: candidate space requires sampled guess evaluation to respect budget.",
            )

    def select_and_solve(self, belief_state: BeliefState) -> SolverResult:
        """Execute the appropriate algorithm based on dynamic workload profiling and budgets."""
        profile = self.profile_workload(belief_state)

        # 1. Base case: 1 candidate
        if belief_state.size == 1:
            only = belief_state.candidates[0]
            g_score = GuessScore(only, 0.0, True, 0, 0.0, 0.0, 1)
            telemetry = SearchTelemetry(
                method_name="Deductive Elimination",
                objective="direct_deduction",
                initial_candidates_count=1,
                guesses_considered_count=1,
                nodes_evaluated=1,
                max_depth_reached=1,
                elapsed_time_ms=0.01,
                is_exact=True,
                is_budget_exhausted=False,
                stopping_reason="Single consistent candidate remaining",
                best_score=0.0,
                top_guesses=(g_score,),
            )
            return SolverResult(guess=only, telemetry=telemetry)

        # 2. Exact Policy Search for small instances
        if "Exact" in profile.recommended_strategy:
            try:
                exact_solver = ExactPolicySolver(
                    self._config,
                    objective=ExactObjective.EXPECTED_TOTAL_GUESSES,
                    max_states=self._budget.max_nodes or 25000,
                )
                return exact_solver.solve(belief_state, max_time_seconds=self._budget.max_time_seconds)
            except (ExactSearchLimitExceeded, Exception):
                # Safe fallback to bounded or heuristic
                pass

        # 3. Bounded Expectimax
        if "Expectimax" in profile.recommended_strategy:
            try:
                exp_solver = BoundedExpectimaxSolver(
                    self._config,
                    budget=self._budget,
                    max_depth=min(2, self._budget.max_depth or 2),
                )
                return exp_solver.solve(belief_state)
            except Exception:
                pass

        # 4. Large-instance sampled heuristic with anytime entropy termination
        if "Sampled" in profile.recommended_strategy:
            sample_size = min(300, self._budget.max_candidate_guesses or 300)
            sample_guesses = self._cand_gen.generate_candidate_guesses(
                belief_state,
                policy=GuessFilterPolicy.HYBRID_SAMPLED,
                max_guesses=sample_size,
            )
            heuristic = AnytimeEntropyHeuristic(
                timeline_seconds=self._budget.max_time_seconds or 2.0,
                max_memory_mb=self._budget.max_memory_mb or 512.0,
            )
            return heuristic.select_best_guess(
                sample_guesses,
                belief_state,
                max_time_seconds=self._budget.max_time_seconds,
            )

        # 5. Default Standard Anytime Entropy Heuristic
        heuristic = AnytimeEntropyHeuristic(
            timeline_seconds=self._budget.max_time_seconds or 2.0,
            max_memory_mb=self._budget.max_memory_mb or 512.0,
        )
        guesses = self._cand_gen.generate_candidate_guesses(
            belief_state,
            policy=GuessFilterPolicy.ALL_LEGAL_CODES,
            max_guesses=self._budget.max_candidate_guesses,
        )
        return heuristic.select_best_guess(
            guesses,
            belief_state,
            max_time_seconds=self._budget.max_time_seconds,
        )
