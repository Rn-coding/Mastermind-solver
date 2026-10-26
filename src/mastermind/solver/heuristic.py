"""Classical heuristic evaluation strategies for Mastermind."""

from __future__ import annotations
from abc import ABC, abstractmethod
import math
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from mastermind.observation import Code, Feedback
from mastermind.solver.belief_state import BeliefState
from mastermind.telemetry import GuessScore, SearchTelemetry, SolverResult


def compute_partition_metrics(
    partitions: Dict[Feedback, List[Code]],
    total_candidates: int,
    is_candidate: bool,
    guess: Code,
) -> Tuple[int, float, float, int]:
    """Compute worst_case, expected_remaining, entropy_bits, partition_count."""
    if total_candidates == 0:
        return 0, 0.0, 0.0, 0

    worst_case = max(len(part) for part in partitions.values()) if partitions else 0
    partition_count = len(partitions)

    # Expected remaining candidates: sum(P(fb) * |C_fb|) = sum(|C_fb|^2) / |C|
    expected_remaining = sum((len(part) ** 2) for part in partitions.values()) / total_candidates

    # Entropy in bits: -sum(P(fb) * log2(P(fb)))
    entropy_bits = 0.0
    for part in partitions.values():
        p = len(part) / total_candidates
        if p > 0:
            entropy_bits -= p * math.log2(p)

    return worst_case, expected_remaining, entropy_bits, partition_count


class BaseHeuristic(ABC):
    """Abstract base class for 1-ply partition-based heuristic evaluators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the heuristic algorithm."""
        pass

    @property
    @abstractmethod
    def objective_name(self) -> str:
        """Name of the optimization objective."""
        pass

    @abstractmethod
    def score_guess(
        self,
        guess: Code,
        partitions: Dict[Feedback, List[Code]],
        total_candidates: int,
        is_candidate: bool,
    ) -> float:
        """Compute the numeric score to be optimized.

        Convention: Solvers MINIMIZE this score (lower is better).
        For heuristics that maximize (like entropy), return negative score.
        """
        pass

    def evaluate_guess(self, guess: Code, belief_state: BeliefState) -> GuessScore:
        """Evaluate a single guess against the current belief state."""
        partitions = belief_state.partition(guess)
        is_cand = belief_state.contains(guess)
        worst_case, exp_rem, entropy, part_count = compute_partition_metrics(
            partitions, belief_state.size, is_cand, guess
        )
        score = self.score_guess(guess, partitions, belief_state.size, is_cand)
        return GuessScore(
            guess=guess,
            score=score,
            is_candidate=is_cand,
            worst_case_remaining=worst_case,
            expected_remaining=exp_rem,
            entropy_bits=entropy,
            partition_count=part_count,
        )

    def select_best_guess(
        self,
        guesses_to_eval: Sequence[Code],
        belief_state: BeliefState,
        max_time_seconds: Optional[float] = None,
        deadline: Optional[float] = None,
    ) -> SolverResult:
        """Evaluate candidate guesses and select the best according to the heuristic."""
        start_time = time.perf_counter()
        effective_deadline = deadline or (start_time + max_time_seconds if max_time_seconds else None)

        # Base case: exactly 1 candidate remaining -> only 1 logical guess
        if belief_state.size == 1:
            only_guess = belief_state.candidates[0]
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            g_score = GuessScore(
                guess=only_guess,
                score=0.0,
                is_candidate=True,
                worst_case_remaining=0,
                expected_remaining=0.0,
                entropy_bits=0.0,
                partition_count=1,
            )
            telemetry = SearchTelemetry(
                method_name=self.name,
                objective=self.objective_name,
                initial_candidates_count=1,
                guesses_considered_count=1,
                nodes_evaluated=1,
                max_depth_reached=1,
                elapsed_time_ms=elapsed_ms,
                is_exact=True,
                is_budget_exhausted=False,
                stopping_reason="Single remaining candidate solved",
                best_score=0.0,
                top_guesses=(g_score,),
            )
            return SolverResult(guess=only_guess, telemetry=telemetry)

        best_guess: Optional[Code] = None
        best_score = float("inf")
        best_guess_metrics: Optional[GuessScore] = None
        all_evaluated: List[GuessScore] = []
        nodes_evaluated = 0
        budget_exhausted = False
        stopping_reason = "Completed full heuristic evaluation"

        for idx, guess in enumerate(guesses_to_eval):
            # Check timeout
            if effective_deadline and time.perf_counter() >= effective_deadline and idx > 0:
                budget_exhausted = True
                stopping_reason = f"Time budget elapsed after evaluating {idx} guesses"
                break

            g_score = self.evaluate_guess(guess, belief_state)
            nodes_evaluated += 1
            all_evaluated.append(g_score)

            # Tie-breaking logic:
            # 1. Lower score is better
            # 2. If score tied, prefer guess in belief state (is_candidate == True)
            is_better = False
            if best_guess is None:
                is_better = True
            elif g_score.score < best_score:
                is_better = True
            elif math.isclose(g_score.score, best_score, rel_tol=1e-9):
                # Tie: candidate secret preferred over non-candidate secret
                if g_score.is_candidate and not best_guess_metrics.is_candidate:
                    is_better = True

            if is_better:
                best_score = g_score.score
                best_guess = guess
                best_guess_metrics = g_score

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Sort top 5 guesses for telemetry
        all_evaluated.sort(key=lambda x: (x.score, not x.is_candidate))
        top_5 = tuple(all_evaluated[:5])

        # Partition summary for best guess
        part_summary = None
        if best_guess:
            partitions = belief_state.partition(best_guess)
            part_summary = {str(fb): len(p) for fb, p in partitions.items()}

        telemetry = SearchTelemetry(
            method_name=self.name,
            objective=self.objective_name,
            initial_candidates_count=belief_state.size,
            guesses_considered_count=len(guesses_to_eval),
            nodes_evaluated=nodes_evaluated,
            max_depth_reached=1,
            elapsed_time_ms=elapsed_ms,
            is_exact=False,
            is_budget_exhausted=budget_exhausted,
            stopping_reason=stopping_reason,
            best_score=best_score,
            top_guesses=top_5,
            partition_summary=part_summary,
        )

        # Fallback to first available guess if none evaluated
        selected_guess = best_guess if best_guess is not None else guesses_to_eval[0]
        return SolverResult(guess=selected_guess, telemetry=telemetry)


class KnuthMinimaxHeuristic(BaseHeuristic):
    """Knuth (1977) Minimax Heuristic: Minimize the worst-case remaining candidates.

    Score = max_{fb} |C_fb|. Tie-breaker: prefer candidate secret.
    """

    @property
    def name(self) -> str:
        return "Knuth Minimax (Worst-Case)"

    @property
    def objective_name(self) -> str:
        return "minimize_worst_case_remaining"

    def score_guess(
        self,
        guess: Code,
        partitions: Dict[Feedback, List[Code]],
        total_candidates: int,
        is_candidate: bool,
    ) -> float:
        if not partitions:
            return float("inf")
        worst_case = max(len(part) for part in partitions.values())
        return float(worst_case)


class EntropyHeuristic(BaseHeuristic):
    """Information Gain / Entropy Heuristic (Shannon 1948, Bestavros 1986).

    Maximizes Shannon entropy H(g) = -sum(P(fb) * log2(P(fb))).
    Score returned is -H(g) so lower score equals higher information gain.
    """

    @property
    def name(self) -> str:
        return "Shannon Entropy (Information Gain)"

    @property
    def objective_name(self) -> str:
        return "maximize_shannon_entropy"

    def score_guess(
        self,
        guess: Code,
        partitions: Dict[Feedback, List[Code]],
        total_candidates: int,
        is_candidate: bool,
    ) -> float:
        if total_candidates == 0 or not partitions:
            return 0.0
        entropy = 0.0
        for part in partitions.values():
            p = len(part) / total_candidates
            if p > 0:
                entropy -= p * math.log2(p)
        return -entropy


class ExpectedSizeHeuristic(BaseHeuristic):
    """Irving (1978) Expected Remaining Candidate Size Heuristic.

    Minimizes expected size sum(P(fb) * |C_fb|) = sum(|C_fb|^2) / |C|.
    """

    @property
    def name(self) -> str:
        return "Irving Expected Size"

    @property
    def objective_name(self) -> str:
        return "minimize_expected_remaining_candidates"

    def score_guess(
        self,
        guess: Code,
        partitions: Dict[Feedback, List[Code]],
        total_candidates: int,
        is_candidate: bool,
    ) -> float:
        if total_candidates == 0 or not partitions:
            return float("inf")
        exp_size = sum((len(part) ** 2) for part in partitions.values()) / total_candidates
        return float(exp_size)


class PartitionHeuristic(BaseHeuristic):
    """Kooi (2005) Most Parts Heuristic.

    Maximizes number of non-empty feedback outcome buckets (minimizes -count).
    """

    @property
    def name(self) -> str:
        return "Most Parts (Partition Count)"

    @property
    def objective_name(self) -> str:
        return "maximize_partition_count"

    def score_guess(
        self,
        guess: Code,
        partitions: Dict[Feedback, List[Code]],
        total_candidates: int,
        is_candidate: bool,
    ) -> float:
        return -float(len(partitions))
