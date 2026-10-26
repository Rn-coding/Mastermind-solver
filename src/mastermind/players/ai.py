"""AI player implementation interacting with the game engine solely via observations."""

from __future__ import annotations
from typing import Optional, Sequence
from mastermind.observation import Code, Observation
from mastermind.players.base import BasePlayer
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.candidates import CandidateGenerator, GuessFilterPolicy
from mastermind.solver.heuristic import BaseHeuristic, EntropyHeuristic
from mastermind.telemetry import SolverResult


class AIPlayer(BasePlayer):
    """An AI player that deduces secrets using belief-state filtering and search heuristics."""

    def __init__(
        self,
        name: str = "Mastermind AI",
        heuristic: Optional[BaseHeuristic] = None,
        filter_policy: GuessFilterPolicy = GuessFilterPolicy.ALL_LEGAL_CODES,
        use_first_guess_canonical: bool = True,
    ) -> None:
        self._name = name
        self._heuristic = heuristic or EntropyHeuristic()
        self._filter_policy = filter_policy
        self._use_first_guess_canonical = use_first_guess_canonical

        self._belief_state: Optional[BeliefState] = None
        self._cand_gen: Optional[CandidateGenerator] = None
        self._last_result: Optional[SolverResult] = None

    @property
    def last_result(self) -> Optional[SolverResult]:
        """Telemetry and metrics from the most recent decision."""
        return self._last_result

    @property
    def belief_state(self) -> Optional[BeliefState]:
        """Active belief state tracking candidate secrets."""
        return self._belief_state

    def get_name(self) -> str:
        return self._name

    def choose_guess(self, observation: Observation) -> Sequence[int]:
        """Select the next guess based solely on the public observation."""
        config = observation.config

        # Initialize or update belief state
        if self._belief_state is None:
            self._belief_state = BeliefState(config)
            self._cand_gen = CandidateGenerator(config)

        # Update belief state with any new turns
        self._belief_state.update_from_observation(observation)

        # Optimization: Turn 1 symmetry reduction
        if observation.turn_number == 0 and self._use_first_guess_canonical and self._cand_gen:
            first_guess = self._cand_gen.get_canonical_first_guess()
            # Still evaluate metrics for diagnostics
            result = self._heuristic.evaluate_guess(first_guess, self._belief_state)
            self._last_result = self._heuristic.select_best_guess([first_guess], self._belief_state)
            return first_guess

        # Generate candidates to consider
        assert self._cand_gen is not None
        guesses_to_eval = self._cand_gen.generate_candidate_guesses(
            self._belief_state, policy=self._filter_policy
        )

        # Evaluate and choose best guess
        result = self._heuristic.select_best_guess(guesses_to_eval, self._belief_state)
        self._last_result = result
        return result.guess
