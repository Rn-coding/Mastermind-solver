"""Resource budgets and execution accounting for search algorithms."""

from __future__ import annotations
from dataclasses import dataclass, field
import time
from typing import Optional


@dataclass
class SearchBudget:
    """Configurable resource limits for solver search execution.

    Attributes:
        max_time_seconds: Maximum wall-clock seconds for a single turn decision.
        max_nodes: Maximum expanded/evaluated states or guesses.
        max_depth: Maximum search lookahead plies.
        max_candidate_guesses: Limit on candidate guesses considered in partition loops.
    """

    max_time_seconds: Optional[float] = 3.0
    max_nodes: Optional[int] = 50000
    max_depth: Optional[int] = 3
    max_candidate_guesses: Optional[int] = 300

    # Runtime tracking
    _start_time: float = field(default_factory=time.perf_counter, init=False)
    _nodes_evaluated: int = field(default=0, init=False)
    _is_exhausted: bool = field(default=False, init=False)
    _exhaustion_reason: str = field(default="", init=False)

    def reset(self) -> None:
        """Reset budget tracking before starting a new search step."""
        self._start_time = time.perf_counter()
        self._nodes_evaluated = 0
        self._is_exhausted = False
        self._exhaustion_reason = ""

    @property
    def elapsed_seconds(self) -> float:
        return time.perf_counter() - self._start_time

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_seconds * 1000.0

    @property
    def nodes_evaluated(self) -> int:
        return self._nodes_evaluated

    @property
    def is_exhausted(self) -> bool:
        return self._is_exhausted

    @property
    def exhaustion_reason(self) -> str:
        return self._exhaustion_reason

    def tick_node(self) -> bool:
        """Increment evaluated node counter and check resource limits.

        Returns:
            True if search can continue, False if budget has been exhausted.
        """
        self._nodes_evaluated += 1

        if self.max_nodes and self._nodes_evaluated >= self.max_nodes:
            self._is_exhausted = True
            self._exhaustion_reason = f"Node limit reached ({self._nodes_evaluated} nodes)"
            return False

        if self.max_time_seconds and self.elapsed_seconds >= self.max_time_seconds:
            self._is_exhausted = True
            self._exhaustion_reason = f"Time budget elapsed ({self.elapsed_seconds:.3f}s >= {self.max_time_seconds}s)"
            return False

        return True
