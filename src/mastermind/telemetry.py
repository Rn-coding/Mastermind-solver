"""Diagnostic telemetry and search result contracts."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
from mastermind.observation import Code


@dataclass(frozen=True)
class GuessScore:
    """Evaluation score and metrics for a considered guess."""

    guess: Code
    score: float
    is_candidate: bool
    worst_case_remaining: int
    expected_remaining: float
    entropy_bits: float
    partition_count: int


@dataclass(frozen=True)
class SearchTelemetry:
    """Structured diagnostic telemetry produced during a solver decision."""

    method_name: str
    objective: str
    initial_candidates_count: int
    guesses_considered_count: int
    nodes_evaluated: int
    max_depth_reached: int
    elapsed_time_ms: float
    is_exact: bool
    is_budget_exhausted: bool
    stopping_reason: str
    best_score: float
    top_guesses: Tuple[GuessScore, ...] = field(default_factory=tuple)
    partition_summary: Optional[Dict[str, int]] = None


@dataclass(frozen=True)
class SolverResult:
    """Complete response from an AI solver decision step."""

    guess: Code
    telemetry: SearchTelemetry
