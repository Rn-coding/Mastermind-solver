"""Configuration for Mastermind game settings."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence, Union

DEFAULT_COLOR_NAMES = ("Red", "Green", "Blue", "Yellow", "Orange", "Purple", "Cyan", "Magenta")


@dataclass(frozen=True)
class GameConfig:
    """Immutable configuration for a Mastermind match.

    Attributes:
        num_pegs: Number of positions/pegs in the code (secret/guess length).
        num_colors: Number of distinct colors available (represented as integers 0..num_colors-1).
        allow_repeats: Whether colors may be repeated in a code.
        max_guesses: Optional maximum allowed guesses before the game terminates. None means unlimited.
        seed: Optional random seed for reproducible secret generation (int or string).
        color_names: Optional sequence of friendly color display names.
    """

    num_pegs: int = 4
    num_colors: int = 6
    allow_repeats: bool = True
    max_guesses: Optional[int] = 10
    seed: Optional[Union[int, str]] = None
    color_names: Optional[Sequence[str]] = None

    def __post_init__(self) -> None:
        if self.num_pegs < 1:
            raise ValueError(f"num_pegs must be at least 1, got {self.num_pegs}")
        if self.num_colors < 1:
            raise ValueError(f"num_colors must be at least 1, got {self.num_colors}")
        if not self.allow_repeats and self.num_pegs > self.num_colors:
            raise ValueError(
                f"num_pegs ({self.num_pegs}) cannot exceed num_colors ({self.num_colors}) "
                "when allow_repeats is False"
            )
        if self.max_guesses is not None and self.max_guesses < 1:
            raise ValueError(f"max_guesses must be positive, got {self.max_guesses}")

    def get_color_name(self, color_idx: int) -> str:
        """Return a readable name for a color index."""
        if not (0 <= color_idx < self.num_colors):
            raise IndexError(f"Color index {color_idx} out of range [0, {self.num_colors - 1}]")
        if self.color_names and color_idx < len(self.color_names):
            return self.color_names[color_idx]
        if color_idx < len(DEFAULT_COLOR_NAMES):
            return DEFAULT_COLOR_NAMES[color_idx]
        return f"Color-{color_idx}"
