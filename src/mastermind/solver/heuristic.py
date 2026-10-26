"""Classical heuristic evaluation strategies for Mastermind."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from mastermind.observation import Code, Feedback
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.budget import get_current_memory_mb
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


@dataclass(frozen=True)
class PartitionOutcome:
    """Feedback outcome details for partition distribution analysis."""

    feedback: Feedback
    count: int
    probability: float
    percentage: float


@dataclass(frozen=True)
class DetailedGuessAnalysis:
    """Detailed information-theoretic evaluation of a candidate guess."""

    guess: Code
    entropy_bits: float
    worst_case_remaining: int
    expected_remaining: float
    is_candidate: bool
    total_candidates: int
    partition_count: int
    outcomes: Tuple[PartitionOutcome, ...]


def analyze_guess_partitions(guess: Code, belief_state: BeliefState) -> DetailedGuessAnalysis:
    """Compute complete partition distribution frequencies and information entropy for a guess."""
    partitions = belief_state.partition(guess)
    total_cands = belief_state.size
    is_cand = belief_state.contains(guess)
    worst_case, exp_rem, entropy, part_count = compute_partition_metrics(
        partitions, total_cands, is_cand, guess
    )

    outcomes: List[PartitionOutcome] = []
    for fb, part in partitions.items():
        cnt = len(part)
        prob = cnt / total_cands if total_cands > 0 else 0.0
        outcomes.append(PartitionOutcome(fb, cnt, prob, prob * 100.0))

    # Sort descending by frequency
    outcomes.sort(key=lambda x: (x.count, x.feedback.exact, x.feedback.misplaced), reverse=True)

    return DetailedGuessAnalysis(
        guess=guess,
        entropy_bits=entropy,
        worst_case_remaining=worst_case,
        expected_remaining=exp_rem,
        is_candidate=is_cand,
        total_candidates=total_cands,
        partition_count=part_count,
        outcomes=tuple(outcomes),
    )


class AnytimeEntropyHeuristic(BaseHeuristic):
    """Anytime entropy heuristic that terminates on time/memory limits and returns maximum entropy guess."""

    def __init__(
        self,
        timeline_seconds: float = 2.0,
        max_memory_mb: float = 512.0,
    ) -> None:
        self.timeline_seconds = timeline_seconds
        self.max_memory_mb = max_memory_mb

    @property
    def name(self) -> str:
        return "Anytime Maximum Entropy"

    @property
    def objective_name(self) -> str:
        return "maximize_shannon_entropy_anytime"

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

    def select_best_guess(
        self,
        guesses_to_eval: Sequence[Code],
        belief_state: BeliefState,
        max_time_seconds: Optional[float] = None,
        deadline: Optional[float] = None,
    ) -> SolverResult:
        start_time = time.perf_counter()
        effective_timeline = max_time_seconds or self.timeline_seconds
        effective_deadline = deadline or (start_time + effective_timeline)

        if belief_state.size == 1:
            only_guess = belief_state.candidates[0]
            g_score = GuessScore(only_guess, 0.0, True, 0, 0.0, 0.0, 1)
            telemetry = SearchTelemetry(
                method_name=self.name,
                objective=self.objective_name,
                initial_candidates_count=1,
                guesses_considered_count=1,
                nodes_evaluated=1,
                max_depth_reached=1,
                elapsed_time_ms=0.01,
                is_exact=True,
                is_budget_exhausted=False,
                stopping_reason="Single remaining candidate solved",
                best_score=0.0,
                top_guesses=(g_score,),
            )
            return SolverResult(guess=only_guess, telemetry=telemetry)

        best_guess: Optional[Code] = None
        best_entropy = -1.0
        best_metrics: Optional[GuessScore] = None
        all_evaluated: List[GuessScore] = []
        nodes_evaluated = 0
        budget_exhausted = False
        stopping_reason = "Completed full anytime candidate evaluation"

        for idx, guess in enumerate(guesses_to_eval):
            now = time.perf_counter()
            # Time check
            if now >= effective_deadline and idx > 0:
                budget_exhausted = True
                stopping_reason = (
                    f"Timeline elapsed ({(now - start_time):.2f}s >= {effective_timeline:.2f}s). "
                    f"Applied guess with maximum evaluated entropy ({best_entropy:.3f} bits)."
                )
                break

            # Memory check every 25 guesses
            if idx % 25 == 0 and idx > 0:
                mem = get_current_memory_mb()
                if mem > self.max_memory_mb:
                    budget_exhausted = True
                    stopping_reason = (
                        f"Memory budget reached ({mem:.1f}MB >= {self.max_memory_mb:.1f}MB). "
                        f"Applied guess with maximum evaluated entropy ({best_entropy:.3f} bits)."
                    )
                    break

            g_score = self.evaluate_guess(guess, belief_state)
            nodes_evaluated += 1
            all_evaluated.append(g_score)

            # Maximize entropy
            curr_entropy = g_score.entropy_bits
            is_better = False
            if best_guess is None:
                is_better = True
            elif curr_entropy > best_entropy:
                is_better = True
            elif math.isclose(curr_entropy, best_entropy, rel_tol=1e-9):
                # Tie-breaking: candidate over non-candidate
                if g_score.is_candidate and not (best_metrics and best_metrics.is_candidate):
                    is_better = True

            if is_better:
                best_entropy = curr_entropy
                best_guess = guess
                best_metrics = g_score

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        all_evaluated.sort(key=lambda x: (-x.entropy_bits, not x.is_candidate))
        top_5 = tuple(all_evaluated[:5])

        selected = best_guess if best_guess is not None else guesses_to_eval[0]
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
            best_score=-best_entropy,
            top_guesses=top_5,
        )

        return SolverResult(guess=selected, telemetry=telemetry)
