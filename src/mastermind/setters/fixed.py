"""Fixed and random secret setters for standard Mastermind play."""

from __future__ import annotations
import random
from typing import Optional, Sequence, Union
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback
from mastermind.rules import calculate_feedback, validate_code
from mastermind.setters.base import BaseSetter


class KnownFixedSetter(BaseSetter):
    """Setter that uses an explicitly provided secret code."""

    def __init__(self, secret: Sequence[int], config: Optional[GameConfig] = None) -> None:
        self._secret: Code = tuple(secret)
        if config is not None:
            self.initialize(config)

    def initialize(self, config: GameConfig) -> None:
        validate_code(self._secret, config)
        self._config = config

    def evaluate_guess(self, guess: Code) -> Feedback:
        return calculate_feedback(self._secret, guess)

    def reveal_secret(self) -> Code:
        return self._secret


class RandomFixedSetter(BaseSetter):
    """Setter that randomly generates a secret code at initialization."""

    def __init__(self, seed: Optional[Union[int, str]] = None) -> None:
        self._seed = seed
        self._secret: Optional[Code] = None
        self._config: Optional[GameConfig] = None

    def initialize(self, config: GameConfig) -> None:
        self._config = config
        effective_seed = self._seed if self._seed is not None else config.seed
        rng = random.Random(effective_seed)

        colors = list(range(config.num_colors))
        if config.allow_repeats:
            self._secret = tuple(rng.choices(colors, k=config.num_pegs))
        else:
            self._secret = tuple(rng.sample(colors, k=config.num_pegs))

    def evaluate_guess(self, guess: Code) -> Feedback:
        if self._secret is None:
            raise RuntimeError("Setter has not been initialized with GameConfig.")
        return calculate_feedback(self._secret, guess)

    def reveal_secret(self) -> Optional[Code]:
        return self._secret
