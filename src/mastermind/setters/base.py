"""Base interface for Mastermind code setters."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback


class BaseSetter(ABC):
    """Abstract interface for all code setter strategies (fixed, random, adversarial)."""

    @abstractmethod
    def initialize(self, config: GameConfig) -> None:
        """Initialize the setter with the match configuration."""
        pass

    @abstractmethod
    def evaluate_guess(self, guess: Code) -> Feedback:
        """Evaluate a guess and return feedback according to the setter's rule/secret."""
        pass

    @abstractmethod
    def reveal_secret(self) -> Optional[Code]:
        """Reveal the secret code if applicable (e.g. for inspection post-game)."""
        pass
