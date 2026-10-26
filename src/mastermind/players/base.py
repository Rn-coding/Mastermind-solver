"""Base player interface for human and AI participants."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Sequence
from mastermind.observation import Observation


class BasePlayer(ABC):
    """Abstract interface for any Mastermind player (Human or AI).

    Players interact exclusively through public Observations.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return the player's display name."""
        pass

    @abstractmethod
    def choose_guess(self, observation: Observation) -> Sequence[int]:
        """Choose a guess based on the current public observation.

        Args:
            observation: The public game state including history and configuration.

        Returns:
            A sequence of integers representing the chosen color pegs.
        """
        pass
