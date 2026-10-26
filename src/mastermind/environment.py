"""Authoritative Mastermind game environment."""

from __future__ import annotations
from typing import List, Optional, Sequence
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback, Observation, TurnRecord, TurnResult
from mastermind.rules import validate_code
from mastermind.setters.base import BaseSetter
from mastermind.setters.fixed import RandomFixedSetter


class MastermindEnvironment:
    """Authoritative environment managing game rules, turn loop, and secret encapsulation."""

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        setter: Optional[BaseSetter] = None,
    ) -> None:
        self._config = config or GameConfig()
        self._setter = setter or RandomFixedSetter(seed=self._config.seed)
        self._history: List[TurnRecord] = []
        self._turn_number: int = 0
        self._is_solved: bool = False
        self._is_terminal: bool = False

        # Initialize the setter with the active configuration
        self._setter.initialize(self._config)

    @property
    def config(self) -> GameConfig:
        """Active game configuration."""
        return self._config

    @property
    def turn_number(self) -> int:
        """Current turn number (0 before any guess)."""
        return self._turn_number

    @property
    def is_terminal(self) -> bool:
        """Whether the game has ended (either solved or guess limit reached)."""
        return self._is_terminal

    @property
    def is_solved(self) -> bool:
        """Whether the hidden secret was successfully identified."""
        return self._is_solved

    def reset(
        self,
        config: Optional[GameConfig] = None,
        setter: Optional[BaseSetter] = None,
    ) -> Observation:
        """Reset the game environment for a new match."""
        if config is not None:
            self._config = config
        if setter is not None:
            self._setter = setter

        self._history = []
        self._turn_number = 0
        self._is_solved = False
        self._is_terminal = False

        self._setter.initialize(self._config)
        return self.get_observation()

    def submit_guess(self, guess: Sequence[int]) -> TurnResult:
        """Submit a guess to the environment and receive feedback.

        Raises:
            RuntimeError: If game is already terminal.
            ValueError: If the guess does not conform to game configuration.
        """
        if self._is_terminal:
            raise RuntimeError("Cannot submit guess: game is already in a terminal state.")

        guess_tuple: Code = tuple(guess)
        validate_code(guess_tuple, self._config)

        self._turn_number += 1
        feedback: Feedback = self._setter.evaluate_guess(guess_tuple)

        self._is_solved = feedback.is_solved(self._config.num_pegs)
        limit_reached = (
            self._config.max_guesses is not None
            and self._turn_number >= self._config.max_guesses
        )
        self._is_terminal = self._is_solved or limit_reached

        record = TurnRecord(
            turn=self._turn_number,
            guess=guess_tuple,
            feedback=feedback,
        )
        self._history.append(record)

        return TurnResult(
            turn=self._turn_number,
            guess=guess_tuple,
            feedback=feedback,
            is_terminal=self._is_terminal,
            is_solved=self._is_solved,
        )

    def get_observation(self) -> Observation:
        """Get the current public observation.

        The observation contains only public game configurations and turn history.
        The secret is strictly isolated on the environment/setter side.
        """
        return Observation(
            config=self._config,
            history=tuple(self._history),
            turn_number=self._turn_number,
            is_terminal=self._is_terminal,
            is_solved=self._is_solved,
        )

    def reveal_secret(self, force: bool = False) -> Optional[Code]:
        """Reveal the secret code.

        By default, only allowed once the game has reached a terminal state.
        Args:
            force: If True, allows revealing during a match (useful for debugging/testing).
        """
        if not self._is_terminal and not force:
            raise PermissionError("Cannot reveal secret while game is in progress.")
        return self._setter.reveal_secret()
