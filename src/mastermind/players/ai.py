"""AI player implementation interacting with the game engine solely via observations."""

from __future__ import annotations
from typing import Optional, Sequence
from mastermind.observation import Code, Observation
from mastermind.players.base import BasePlayer
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.budget import SearchBudget
from mastermind.solver.candidates import CandidateGenerator, GuessFilterPolicy
from mastermind.solver.heuristic import BaseHeuristic, EntropyHeuristic
from mastermind.solver.strategy_selector import StrategySelector
from mastermind.telemetry import SolverResult


class AIPlayer(BasePlayer):
    """An AI player that deduces secrets using belief-state filtering and search heuristics."""

    def __init__(
        self,
        name: str = "Mastermind AI",
        heuristic: Optional[BaseHeuristic] = None,
        filter_policy: GuessFilterPolicy = GuessFilterPolicy.ALL_LEGAL_CODES,
        use_first_guess_canonical: bool = True,
        use_strategy_selector: bool = False,
        budget: Optional[SearchBudget] = None,
    ) -> None:
        self._name = name
        self._heuristic = heuristic or EntropyHeuristic()
        self._filter_policy = filter_policy
        self._use_first_guess_canonical = use_first_guess_canonical
        self._use_strategy_selector = use_strategy_selector
        self._budget = budget or SearchBudget()

        self._belief_state: Optional[BeliefState] = None
        self._cand_gen: Optional[CandidateGenerator] = None
        self._selector: Optional[StrategySelector] = None
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
            if self._use_strategy_selector:
                self._selector = StrategySelector(config, self._budget)

        # Update belief state with any new turns
        self._belief_state.update_from_observation(observation)

        # Optimization: Turn 1 symmetry reduction
        if observation.turn_number == 0 and self._use_first_guess_canonical and self._cand_gen:
            first_guess = self._cand_gen.get_canonical_first_guess()
            self._last_result = self._heuristic.select_best_guess([first_guess], self._belief_state)
            return first_guess

        # If adaptive strategy selector is enabled, dynamically choose solver
        if self._use_strategy_selector and self._selector:
            result = self._selector.select_and_solve(self._belief_state)
            self._last_result = result
            return result.guess

        # Standard heuristic evaluation
        assert self._cand_gen is not None
        guesses_to_eval = self._cand_gen.generate_candidate_guesses(
            self._belief_state,
            policy=self._filter_policy,
            max_guesses=self._budget.max_candidate_guesses,
        )

        result = self._heuristic.select_best_guess(
            guesses_to_eval,
            self._belief_state,
            max_time_seconds=self._budget.max_time_seconds,
        )
        self._last_result = result
        return result.guess
