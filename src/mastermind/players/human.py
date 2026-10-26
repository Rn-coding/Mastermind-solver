"""Human player implementation with flexible input handling."""

from __future__ import annotations
from typing import Callable, Optional, Sequence
from mastermind.observation import Observation
from mastermind.players.base import BasePlayer


class HumanPlayer(BasePlayer):
    """A human player that obtains guesses from an input provider."""

    def __init__(
        self,
        name: str = "Human",
        input_fn: Optional[Callable[[Observation], Sequence[int]]] = None,
    ) -> None:
        self._name = name
        self._input_fn = input_fn

    def get_name(self) -> str:
        return self._name

    def choose_guess(self, observation: Observation) -> Sequence[int]:
        if self._input_fn is None:
            raise RuntimeError("No input provider configured for HumanPlayer.")
        return self._input_fn(observation)
