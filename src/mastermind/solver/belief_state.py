"""Belief-state manager tracking hidden code possibilities consistent with observation history."""

from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback, Observation, TurnRecord
from mastermind.rules import calculate_feedback, generate_all_codes


class InconsistentHistoryError(ValueError):
    """Raised when an observation history eliminates all possible secret codes."""
    pass


class BeliefState:
    """Encapsulates the agent's belief state (the set of possible secrets)."""

    def __init__(
        self,
        config: GameConfig,
        initial_candidates: Optional[Sequence[Code]] = None,
    ) -> None:
        self._config = config
        if initial_candidates is not None:
            self._candidates: List[Code] = list(initial_candidates)
        else:
            self._candidates = generate_all_codes(config)
        self._all_codes_cache: Optional[Tuple[Code, ...]] = None

    @property
    def config(self) -> GameConfig:
        return self._config

    @property
    def candidates(self) -> Tuple[Code, ...]:
        """Current tuple of consistent candidate secret codes."""
        return tuple(self._candidates)

    @property
    def size(self) -> int:
        """Number of remaining candidate codes."""
        return len(self._candidates)

    def is_consistent(self) -> bool:
        """Whether there is at least one candidate consistent with observed feedback."""
        return len(self._candidates) > 0

    def contains(self, code: Code) -> bool:
        """Check if a specific code is still a possible candidate."""
        return code in set(self._candidates)

    def filter_by_turn(self, guess: Code, feedback: Feedback) -> int:
        """Filter current candidates against a single guess and feedback observation.

        Raises:
            InconsistentHistoryError: If the feedback eliminates all remaining candidate codes.
        """
        filtered = [
            cand for cand in self._candidates
            if calculate_feedback(cand, guess) == feedback
        ]
        if not filtered:
            raise InconsistentHistoryError(
                f"No candidate codes remain consistent with guess {guess} and feedback {feedback}."
            )
        self._candidates = filtered
        return len(self._candidates)

    def update_from_observation(self, observation: Observation) -> int:
        """Reconstruct/update belief state from the complete observation history."""
        # Always regenerate from all codes to guarantee consistency
        candidates = generate_all_codes(self._config)
        for record in observation.history:
            candidates = [
                cand for cand in candidates
                if calculate_feedback(cand, record.guess) == record.feedback
            ]
            if not candidates:
                raise InconsistentHistoryError(
                    f"Observation history became inconsistent at turn {record.turn} "
                    f"with guess {record.guess} and feedback {record.feedback}."
                )
        self._candidates = candidates
        return len(self._candidates)

    def partition(self, guess: Code) -> Dict[Feedback, List[Code]]:
        """Partition the current candidate set according to feedback outcomes for a guess.

        Returns:
            Dictionary mapping each possible Feedback outcome to the list of candidates
            producing that feedback.
        """
        partitions: Dict[Feedback, List[Code]] = defaultdict(list)
        for cand in self._candidates:
            fb = calculate_feedback(cand, guess)
            partitions[fb].append(cand)
        return dict(partitions)

    def clone(self) -> BeliefState:
        """Create an independent copy of this belief state."""
        return BeliefState(self._config, initial_candidates=list(self._candidates))
