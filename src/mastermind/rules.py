"""Core rules, validation, feedback calculation, and code space generation."""

from __future__ import annotations
from collections import Counter
import itertools
from typing import List, Sequence, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback


def validate_code(code: Sequence[int], config: GameConfig) -> None:
    """Validate that a code conforms to the given game configuration.

    Raises:
        ValueError: If code length is invalid, colors out of bounds, or illegal repetitions exist.
    """
    if len(code) != config.num_pegs:
        raise ValueError(
            f"Code length mismatch: expected {config.num_pegs} pegs, got {len(code)}: {code}"
        )
    for idx, peg in enumerate(code):
        if not isinstance(peg, int) or peg < 0 or peg >= config.num_colors:
            raise ValueError(
                f"Invalid color '{peg}' at peg {idx}: must be an integer in range [0, {config.num_colors - 1}]"
            )
    if not config.allow_repeats and len(set(code)) != len(code):
        raise ValueError(f"Code contains duplicate colors, which is not permitted: {code}")


def generate_all_codes(config: GameConfig) -> List[Code]:
    """Generate all mathematically legal codes under the configuration.

    Returns:
        List of Code tuples (each of length config.num_pegs with values in 0..num_colors-1).
    """
    colors = range(config.num_colors)
    if config.allow_repeats:
        return list(itertools.product(colors, repeat=config.num_pegs))
    else:
        return list(itertools.permutations(colors, config.num_pegs))


def calculate_feedback(secret: Sequence[int], guess: Sequence[int]) -> Feedback:
    """Calculate exact and misplaced feedback pegs for a guess against a secret.

    Handles repeated colors accurately:
    - Exact matches: positions where secret[i] == guess[i].
    - Misplaced matches: for unmatched positions, min(count_in_secret, count_in_guess)
      for each distinct color.

    Args:
        secret: The hidden sequence of colors.
        guess: The candidate sequence of colors.

    Returns:
        Feedback instance with (exact, misplaced) counts.
    """
    if len(secret) != len(guess):
        raise ValueError(f"Length mismatch: secret has {len(secret)} pegs, guess has {len(guess)} pegs")

    exact = 0
    secret_unmatched: List[int] = []
    guess_unmatched: List[int] = []

    for s_peg, g_peg in zip(secret, guess):
        if s_peg == g_peg:
            exact += 1
        else:
            secret_unmatched.append(s_peg)
            guess_unmatched.append(g_peg)

    if not secret_unmatched:
        return Feedback(exact=exact, misplaced=0)

    secret_counts = Counter(secret_unmatched)
    guess_counts = Counter(guess_unmatched)

    misplaced = sum(
        min(secret_counts[color], guess_counts[color])
        for color in secret_counts
        if color in guess_counts
    )

    return Feedback(exact=exact, misplaced=misplaced)
