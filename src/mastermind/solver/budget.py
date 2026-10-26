"""Resource budgets and execution accounting for search algorithms."""

from __future__ import annotations
from dataclasses import dataclass, field
import time
from typing import Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def get_current_memory_mb() -> float:
    """Return the current process resident memory usage in megabytes."""
    if _HAS_PSUTIL:
        try:
            return psutil.Process().memory_info().rss / (1024.0 * 1024.0)
        except Exception:
            return 0.0
    return 0.0


@dataclass
class SearchBudget:
    """Configurable resource limits for solver search execution.

    Attributes:
        max_time_seconds: Maximum wall-clock seconds for a single turn decision.
        max_nodes: Maximum expanded/evaluated states or guesses.
        max_depth: Maximum search lookahead plies.
        max_candidate_guesses: Limit on candidate guesses considered in partition loops.
        max_memory_mb: Optional memory limit in megabytes before search terminates.
    """

    max_time_seconds: Optional[float] = 3.0
    max_nodes: Optional[int] = 50000
    max_depth: Optional[int] = 3
    max_candidate_guesses: Optional[int] = 300
    max_memory_mb: Optional[float] = 512.0

    # Runtime tracking
    _start_time: float = field(default_factory=time.perf_counter, init=False)
    _start_memory_mb: float = field(default_factory=get_current_memory_mb, init=False)
    _nodes_evaluated: int = field(default=0, init=False)
    _is_exhausted: bool = field(default=False, init=False)
    _exhaustion_reason: str = field(default="", init=False)

    def reset(self) -> None:
        """Reset budget tracking before starting a new search step."""
        self._start_time = time.perf_counter()
        self._start_memory_mb = get_current_memory_mb()
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
    def current_memory_mb(self) -> float:
        return get_current_memory_mb()

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

        # Check memory periodically (every 50 nodes) to minimize syscall overhead
        if self.max_memory_mb and (self._nodes_evaluated % 50 == 0):
            mem = get_current_memory_mb()
            if mem > self.max_memory_mb:
                self._is_exhausted = True
                self._exhaustion_reason = f"Memory limit reached ({mem:.1f} MB >= {self.max_memory_mb:.1f} MB)"
                return False

        return True

        return True
