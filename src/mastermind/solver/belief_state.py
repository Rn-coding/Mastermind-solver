"""Belief-state manager tracking hidden code possibilities consistent with observation history."""

from __future__ import annotations
import math
import random
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback, Observation, TurnRecord
from mastermind.rules import calculate_feedback, generate_all_codes

MAX_EXPLICIT_SPACE = 50000
SAMPLE_POOL_SIZE = 2500


def get_theoretical_space_size(config: GameConfig) -> int:
    """Compute theoretical total code space size |G|."""
    if config.allow_repeats:
        return config.num_colors ** config.num_pegs
    else:
        return math.perm(config.num_colors, config.num_pegs)


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
        self._total_space_size = get_theoretical_space_size(config)
        self._is_sampled = self._total_space_size > MAX_EXPLICIT_SPACE

        if initial_candidates is not None:
            self._candidates: List[Code] = list(initial_candidates)
        elif not self._is_sampled:
            self._candidates = generate_all_codes(config)
        else:
            # Sample candidate pool for large state spaces
            self._candidates = self._sample_consistent_pool(history=(), max_samples=SAMPLE_POOL_SIZE)

    @property
    def config(self) -> GameConfig:
        return self._config

    @property
    def is_sampled(self) -> bool:
        """Whether the belief state represents a sampled candidate pool due to large space size."""
        return self._is_sampled

    @property
    def total_space_size(self) -> int:
        return self._total_space_size

    @property
    def candidates(self) -> Tuple[Code, ...]:
        """Current tuple of consistent candidate secret codes."""
        return tuple(self._candidates)

    @property
    def size(self) -> int:
        """Number of remaining candidate codes in active memory."""
        return len(self._candidates)

    def is_consistent(self) -> bool:
        """Whether there is at least one candidate consistent with observed feedback."""
        return len(self._candidates) > 0

    def contains(self, code: Code) -> bool:
        """Check if a specific code is still a possible candidate."""
        return code in set(self._candidates)

    def _sample_consistent_pool(
        self,
        history: Sequence[TurnRecord],
        max_samples: int = SAMPLE_POOL_SIZE,
        max_attempts: int = 50000,
    ) -> List[Code]:
        """Sample random codes that satisfy all history constraints."""
        rng = random.Random(self._config.seed or 42)
        colors = list(range(self._config.num_colors))
        valid_candidates: Set[Code] = set()

        attempts = 0
        while len(valid_candidates) < max_samples and attempts < max_attempts:
            attempts += 1
            if self._config.allow_repeats:
                candidate = tuple(rng.choices(colors, k=self._config.num_pegs))
            else:
                candidate = tuple(rng.sample(colors, k=self._config.num_pegs))

            if candidate in valid_candidates:
                continue

            # Check consistency with all previous turns
            consistent = True
            for record in history:
                if calculate_feedback(candidate, record.guess) != record.feedback:
                    consistent = False
                    break

            if consistent:
                valid_candidates.add(candidate)

        return list(valid_candidates)

    def filter_by_turn(self, guess: Code, feedback: Feedback) -> int:
        """Filter current candidates against a single guess and feedback observation.

        Raises:
            InconsistentHistoryError: If the feedback eliminates all remaining candidate codes.
        """
        if feedback.is_solved(self._config.num_pegs):
            if self.contains(guess) or self._is_sampled:
                self._candidates = [guess]
                return 1
            raise InconsistentHistoryError(
                f"No candidate codes remain consistent with guess {guess} and feedback {feedback}."
            )

        filtered = [
            cand for cand in self._candidates
            if calculate_feedback(cand, guess) == feedback
        ]

        if not filtered and self._is_sampled:
            # Resample consistent candidates for large state spaces
            resampled = self._sample_consistent_pool(
                history=[TurnRecord(turn=1, guess=guess, feedback=feedback)],
                max_samples=SAMPLE_POOL_SIZE,
            )
            if resampled:
                filtered = resampled

        if not filtered:
            raise InconsistentHistoryError(
                f"No candidate codes remain consistent with guess {guess} and feedback {feedback}."
            )
        self._candidates = filtered
        return len(self._candidates)

    def update_from_observation(self, observation: Observation) -> int:
        """Reconstruct/update belief state from the complete observation history."""
        if not self._is_sampled:
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
        else:
            # Filter existing sampled candidates
            filtered = [
                cand for cand in self._candidates
                if all(calculate_feedback(cand, rec.guess) == rec.feedback for rec in observation.history)
            ]
            # If candidate count drops too low, resample consistent candidates
            if len(filtered) < 100:
                resampled = self._sample_consistent_pool(observation.history, max_samples=SAMPLE_POOL_SIZE)
                combined = set(filtered) | set(resampled)
                filtered = list(combined)

            if not filtered:
                raise InconsistentHistoryError("No candidate codes remain consistent with observation history.")
            self._candidates = filtered

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
