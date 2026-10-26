"""Experiment metrics, trial outcome records, and statistical aggregators."""

from __future__ import annotations
from dataclasses import dataclass, field
import math
import statistics
from typing import Dict, List, Optional, Sequence, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback


@dataclass(frozen=True)
class TurnMetric:
    """Metrics recorded for a single turn in an experiment trial."""

    turn: int
    guess: Code
    feedback: Feedback
    candidates_remaining: int
    entropy_bits: float
    nodes_evaluated: int
    elapsed_time_ms: float
    method_name: str
    is_exact: bool


@dataclass(frozen=True)
class GameTrialResult:
    """Complete results for one game trial in an evaluation run."""

    trial_id: int
    seed: Optional[int | str]
    secret: Code
    solved: bool
    total_turns: int
    total_elapsed_ms: float
    total_nodes: int
    turn_metrics: Tuple[TurnMetric, ...]

    @property
    def mean_turn_time_ms(self) -> float:
        return self.total_elapsed_ms / max(1, self.total_turns)

    @property
    def max_nodes_turn(self) -> int:
        return max((m.nodes_evaluated for m in self.turn_metrics), default=0)


@dataclass(frozen=True)
class ExperimentSummary:
    """Statistical summary across multiple trials under a fixed experiment setting."""

    experiment_name: str
    config: GameConfig
    strategy_name: str
    budget_description: str
    num_trials: int
    solve_rate: float
    mean_guesses: float
    min_guesses: int
    max_guesses: int
    std_guesses: float
    mean_game_time_ms: float
    mean_turn_time_ms: float
    mean_nodes_per_game: float
    total_nodes_evaluated: int
    optimality_gap: Optional[float] = None
    trials: Tuple[GameTrialResult, ...] = field(default_factory=tuple)


def aggregate_experiment(
    experiment_name: str,
    config: GameConfig,
    strategy_name: str,
    budget_description: str,
    trials: Sequence[GameTrialResult],
    exact_reference_mean: Optional[float] = None,
) -> ExperimentSummary:
    """Aggregate individual trial results into a statistical summary."""
    n = len(trials)
    if n == 0:
        raise ValueError("Cannot aggregate empty trial sequence.")

    solved_count = sum(1 for t in trials if t.solved)
    solve_rate = solved_count / n

    guesses = [t.total_turns for t in trials]
    mean_guesses = statistics.mean(guesses)
    min_guesses = min(guesses)
    max_guesses = max(guesses)
    std_guesses = statistics.stdev(guesses) if n > 1 else 0.0

    game_times = [t.total_elapsed_ms for t in trials]
    mean_game_time = statistics.mean(game_times)

    turn_times = [m.elapsed_time_ms for t in trials for m in t.turn_metrics]
    mean_turn_time = statistics.mean(turn_times) if turn_times else 0.0

    nodes = [t.total_nodes for t in trials]
    mean_nodes = statistics.mean(nodes)
    total_nodes = sum(nodes)

    opt_gap = (mean_guesses - exact_reference_mean) if exact_reference_mean is not None else None

    return ExperimentSummary(
        experiment_name=experiment_name,
        config=config,
        strategy_name=strategy_name,
        budget_description=budget_description,
        num_trials=n,
        solve_rate=solve_rate,
        mean_guesses=mean_guesses,
        min_guesses=min_guesses,
        max_guesses=max_guesses,
        std_guesses=std_guesses,
        mean_game_time_ms=mean_game_time,
        mean_turn_time_ms=mean_turn_time,
        mean_nodes_per_game=mean_nodes,
        total_nodes_evaluated=total_nodes,
        optimality_gap=opt_gap,
        trials=tuple(trials),
    )
