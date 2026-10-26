"""Candidate and guess space generators with configurable reduction policies."""

from __future__ import annotations
from enum import Enum
import random
from typing import List, Optional, Sequence, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code
from mastermind.rules import generate_all_codes
from mastermind.solver.belief_state import BeliefState


class GuessFilterPolicy(str, Enum):
    """Policy for selecting candidate guesses to evaluate during a search turn."""

    ALL_LEGAL_CODES = "all_legal_codes"
    CANDIDATES_ONLY = "candidates_only"
    HYBRID_SAMPLED = "hybrid_sampled"


class CandidateGenerator:
    """Generates candidate guesses to evaluate under search and budget constraints."""

    def __init__(self, config: GameConfig) -> None:
        self._config = config
        self._all_codes: Tuple[Code, ...] = tuple(generate_all_codes(config))

    @property
    def all_codes(self) -> Tuple[Code, ...]:
        """All mathematically legal codes under the active configuration."""
        return self._all_codes

    def get_canonical_first_guess(self) -> Code:
        """Return a canonical representative first guess exploiting color symmetry.

        For example, for 4 pegs and 6 colors, (0, 0, 1, 1) or (0, 0, 1, 2) is optimal
        and avoids evaluating all |G| symmetric combinations on Turn 1.
        """
        if self._config.num_pegs <= 1:
            return (0,)
        if not self._config.allow_repeats:
            return tuple(range(min(self._config.num_pegs, self._config.num_colors)))

        # Standard Mastermind convention: 2 of color 0, then 2 of color 1 (or 1 of color 1, 1 of color 2)
        half = max(1, self._config.num_pegs // 2)
        pegs: List[int] = [0] * half
        next_color = 1 if self._config.num_colors > 1 else 0
        while len(pegs) < self._config.num_pegs:
            pegs.append(next_color)
            if self._config.num_pegs - len(pegs) > 1 and next_color + 1 < self._config.num_colors:
                next_color += 1
        return tuple(pegs)

    def generate_candidate_guesses(
        self,
        belief_state: BeliefState,
        policy: GuessFilterPolicy = GuessFilterPolicy.ALL_LEGAL_CODES,
        max_guesses: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> List[Code]:
        """Generate candidate guesses according to the specified policy and budget limits.

        Args:
            belief_state: Current candidate secret possibilities.
            policy: GuessFilterPolicy determining candidate pool.
            max_guesses: Optional maximum number of candidate guesses to return.
            seed: Optional seed for reproducible sampling.

        Returns:
            List of Code tuples to evaluate.
        """
        # If candidate set is tiny (1 or 2 candidates), guessing a remaining candidate is strictly optimal
        if belief_state.size <= 2:
            return list(belief_state.candidates)

        if policy == GuessFilterPolicy.CANDIDATES_ONLY:
            pool = list(belief_state.candidates)
        elif policy == GuessFilterPolicy.ALL_LEGAL_CODES:
            pool = list(self._all_codes)
        elif policy == GuessFilterPolicy.HYBRID_SAMPLED:
            # Include all remaining candidates up to a limit, then sample non-candidates
            cands = list(belief_state.candidates)
            cands_set = set(cands)
            non_cands = [code for code in self._all_codes if code not in cands_set]

            rng = random.Random(seed)
            if max_guesses is not None and len(cands) > max_guesses:
                return rng.sample(cands, max_guesses)

            budget_remaining = (max_guesses - len(cands)) if max_guesses is not None else len(non_cands)
            budget_remaining = max(0, budget_remaining)

            sample_non_cands = rng.sample(non_cands, min(budget_remaining, len(non_cands))) if budget_remaining > 0 else []
            return cands + sample_non_cands
        else:
            pool = list(self._all_codes)

        if max_guesses is not None and len(pool) > max_guesses:
            rng = random.Random(seed)
            # Ensure at least some candidates are prioritized in the sample
            cands = list(belief_state.candidates)
            sample_cands = cands[:max(1, max_guesses // 2)]
            remaining_slots = max_guesses - len(sample_cands)
            other_pool = [c for c in pool if c not in set(sample_cands)]
            sample_others = rng.sample(other_pool, min(remaining_slots, len(other_pool)))
            return sample_cands + sample_others

        return pool
