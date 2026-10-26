"""Contracts and data models for public observations and feedback."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple
from mastermind.config import GameConfig

Code = Tuple[int, ...]


@dataclass(frozen=True)
class Feedback:
    """Feedback for a single Mastermind guess.

    Attributes:
        exact: Number of pegs correct in both color and position (black pegs).
        misplaced: Number of pegs correct in color but incorrect in position (white pegs).
    """

    exact: int
    misplaced: int

    def __post_init__(self) -> None:
        if self.exact < 0 or self.misplaced < 0:
            raise ValueError(f"Feedback counts cannot be negative: exact={self.exact}, misplaced={self.misplaced}")

    def is_solved(self, num_pegs: int) -> bool:
        """Check if this feedback represents a completely solved code."""
        return self.exact == num_pegs

    def __str__(self) -> str:
        return f"(exact={self.exact}, misplaced={self.misplaced})"


@dataclass(frozen=True)
class TurnRecord:
    """Record of a past turn in the game history."""

    turn: int
    guess: Code
    feedback: Feedback


@dataclass(frozen=True)
class TurnResult:
    """Immediate outcome returned after submitting a guess."""

    turn: int
    guess: Code
    feedback: Feedback
    is_terminal: bool
    is_solved: bool


@dataclass(frozen=True)
class Observation:
    """Publicly observable state of the game.

    Crucially, this struct NEVER includes the hidden secret code.
    """

    config: GameConfig
    history: Tuple[TurnRecord, ...]
    turn_number: int
    is_terminal: bool
    is_solved: bool

    @property
    def remaining_guesses(self) -> Optional[int]:
        """Number of remaining allowed guesses, or None if unlimited."""
        if self.config.max_guesses is None:
            return None
        return max(0, self.config.max_guesses - self.turn_number)

    @property
    def last_guess(self) -> Optional[Code]:
        """Return the most recent guess, if any."""
        return self.history[-1].guess if self.history else None

    @property
    def last_feedback(self) -> Optional[Feedback]:
        """Return the most recent feedback, if any."""
        return self.history[-1].feedback if self.history else None
