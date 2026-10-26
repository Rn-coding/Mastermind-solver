"""Tests for AnytimeEntropyHeuristic, partition analysis, and interactive UI commands."""

import pytest
from rich.console import Console

from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
from mastermind.observation import Observation
from mastermind.setters.fixed import KnownFixedSetter, RandomFixedSetter
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.candidates import CandidateGenerator, get_theoretical_space_size
from mastermind.solver.heuristic import (
    AnytimeEntropyHeuristic,
    analyze_guess_partitions,
)
from mastermind.ui.app import MastermindApp
from mastermind.ui.game_view import (
    render_ai_hint,
    render_candidate_inspection,
    render_detailed_guess_eval,
    render_interactive_help,
    render_top_guesses_table,
)


class TestAnytimeEntropyHeuristic:
    def test_maximum_entropy_selection(self):
        config = GameConfig(num_pegs=3, num_colors=3)
        bs = BeliefState(config)
        heuristic = AnytimeEntropyHeuristic(timeline_seconds=1.0)
        res = heuristic.select_best_guess(bs.candidates, bs)

        assert res.guess is not None
        assert res.telemetry.method_name == "Anytime Maximum Entropy"
        assert res.telemetry.best_score <= 0  # Score is -entropy
        # Maximum entropy for 27 candidates is around 2.5 - 3.5 bits
        assert -res.telemetry.best_score > 0

    def test_timeline_exhaustion_interruption(self):
        # 4 pegs, 6 colors (1296 codes)
        config = GameConfig(num_pegs=4, num_colors=6)
        bs = BeliefState(config)
        # Ultra-tight timeline (0.01 seconds) to guarantee interruption mid-search
        heuristic = AnytimeEntropyHeuristic(timeline_seconds=0.01)
        cand_gen = CandidateGenerator(config)
        guesses = cand_gen.generate_candidate_guesses(bs)

        res = heuristic.select_best_guess(guesses, bs)

        assert res.guess is not None
        assert res.telemetry.is_budget_exhausted is True
        assert "Timeline elapsed" in res.telemetry.stopping_reason
        assert "Applied guess with maximum evaluated entropy" in res.telemetry.stopping_reason


class TestDetailedPartitionAnalysis:
    def test_analyze_guess_partitions(self):
        config = GameConfig(num_pegs=3, num_colors=3)
        bs = BeliefState(config)
        analysis = analyze_guess_partitions((0, 1, 2), bs)

        assert analysis.guess == (0, 1, 2)
        assert analysis.total_candidates == 27
        assert analysis.partition_count > 0
        assert analysis.entropy_bits > 0
        assert len(analysis.outcomes) == analysis.partition_count

        # Total counts across outcomes must sum to total candidates
        total_partitioned = sum(o.count for o in analysis.outcomes)
        assert total_partitioned == 27

        # Total probabilities must sum to 1.0 (100%)
        total_pct = sum(o.percentage for o in analysis.outcomes)
        assert pytest.approx(total_pct, rel=1e-3) == 100.0


class TestLargeStateSpaceGuardrails:
    def test_theoretical_space_size_calculation(self):
        cfg = GameConfig(num_pegs=6, num_colors=10, allow_repeats=True)
        assert get_theoretical_space_size(cfg) == 1_000_000

        cfg_perm = GameConfig(num_pegs=4, num_colors=6, allow_repeats=False)
        assert get_theoretical_space_size(cfg_perm) == 360

    def test_large_state_space_belief_state_sampling(self):
        # 7 pegs, 10 colors = 10,000,000 codes (> 2,000,000)
        cfg = GameConfig(num_pegs=7, num_colors=10, allow_repeats=True)
        bs = BeliefState(cfg)

        assert bs.is_sampled is True
        assert bs.size > 0
        assert bs.size <= 2500  # Bounded in RAM

        # Test filtering on large space
        guess = (0, 1, 2, 3, 4, 5, 6)
        setter = KnownFixedSetter(secret=(0, 1, 2, 3, 4, 5, 6), config=cfg)
        fb = setter.evaluate_guess(guess)
        new_size = bs.filter_by_turn(guess, fb)
        assert new_size > 0


class TestInteractiveUICommands:
    @pytest.fixture
    def app_and_env(self):
        console = Console(record=True, width=120)
        app = MastermindApp(console=console)
        config = GameConfig(num_pegs=3, num_colors=3)
        setter = KnownFixedSetter(secret=(0, 1, 2), config=config)
        env = MastermindEnvironment(config=config, setter=setter)
        bs = BeliefState(config)
        return app, env, bs, console

    def test_interactive_help_command(self, app_and_env):
        app, env, bs, console = app_and_env
        handled = app.handle_interactive_command("help", env, bs)
        assert handled is True
        out = console.export_text()
        assert "Available Commands" in out

    def test_interactive_hint_command(self, app_and_env):
        app, env, bs, console = app_and_env
        handled = app.handle_interactive_command("hint", env, bs)
        assert handled is True
        out = console.export_text()
        assert "AI Tactical Hint" in out
        assert "Recommended Move" in out

    def test_interactive_eval_command(self, app_and_env):
        app, env, bs, console = app_and_env
        handled = app.handle_interactive_command("eval 0 1 2", env, bs)
        assert handled is True
        out = console.export_text()
        assert "Partition Distribution Analysis" in out
        assert "Shannon Entropy" in out

    def test_interactive_inspect_command(self, app_and_env):
        app, env, bs, console = app_and_env
        handled = app.handle_interactive_command("inspect", env, bs)
        assert handled is True
        out = console.export_text()
        assert "Candidate State Space Inspection" in out

    def test_interactive_timeline_command(self, app_and_env):
        app, env, bs, console = app_and_env
        handled = app.handle_interactive_command("timeline 1.5", env, bs)
        assert handled is True
        assert app.ai_timeline == 1.5
        out = console.export_text()
        assert "1.5s" in out

    def test_interactive_top_command(self, app_and_env):
        app, env, bs, console = app_and_env
        handled = app.handle_interactive_command("top 3", env, bs)
        assert handled is True
        out = console.export_text()
        assert "Top Candidate Guesses" in out

    def test_eval_table_no_broken_bold_tags(self, app_and_env):
        app, env, bs, console = app_and_env
        analysis = analyze_guess_partitions((0, 1, 2), bs)
        panel = render_detailed_guess_eval(analysis, bs.config)
        test_console = Console(record=True, width=120)
        test_console.print(panel)
        text = test_console.export_text()
        # Verify that '[bold' does not appear as raw leaked text
        assert "[bold" not in text
        assert "Feedback Distribution" in text


class TestFixesAndBackgroundWorker:
    def test_string_seed_determinism(self):
        config1 = GameConfig(num_pegs=4, num_colors=6, seed="abc")
        setter1 = RandomFixedSetter(seed=config1.seed)
        setter1.initialize(config1)

        config2 = GameConfig(num_pegs=4, num_colors=6, seed="abc")
        setter2 = RandomFixedSetter(seed=config2.seed)
        setter2.initialize(config2)

        assert setter1.reveal_secret() == setter2.reveal_secret()

    def test_user_reported_no_repeats_large_setup(self):
        # Exact configuration from user: 8 pegs, 10 colors, allow_repeats=False, seed="abc"
        config = GameConfig(num_pegs=8, num_colors=10, allow_repeats=False, seed="abc")
        setter = RandomFixedSetter(seed=config.seed)
        setter.initialize(config)
        secret = setter.reveal_secret()
        assert len(secret) == 8
        assert len(set(secret)) == 8

        env = MastermindEnvironment(config=config, setter=setter)
        belief_state = BeliefState(config)
        # Verify that 1,814,400 permutation space initializes properly
        assert belief_state.size == 1_814_400

        # Turn 1
        g1 = (0, 1, 2, 3, 4, 5, 6, 7)
        res1 = env.submit_guess(g1)
        # Should filter without raising InconsistentHistoryError
        new_size = belief_state.filter_by_turn(g1, res1.feedback)
        assert new_size > 0
        assert belief_state.contains(secret) is True

    def test_async_anytime_worker(self):
        from mastermind.solver.heuristic import AsyncAnytimeWorker
        config = GameConfig(num_pegs=3, num_colors=3)
        bs = BeliefState(config)
        heuristic = AnytimeEntropyHeuristic(timeline_seconds=1.5)
        guesses = [(0, 1, 2), (0, 0, 0), (1, 1, 1)]

        worker = AsyncAnytimeWorker(
            heuristic=heuristic,
            guesses=guesses,
            belief_state=bs,
            timeline_seconds=1.5,
        )
        # Worker runs in background
        res = worker.stop_and_get_result(timeout=1.0)
        assert res.guess is not None
        assert res.telemetry.nodes_evaluated > 0
