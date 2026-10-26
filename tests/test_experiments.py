"""Unit and integration tests for experiment metrics, runner, and export utilities."""

import csv
import json
from pathlib import Path
from mastermind.config import GameConfig
from mastermind.experiments.export import (
    export_markdown_report,
    export_to_jsonl,
    export_trials_to_csv,
    export_turns_to_csv,
)
from mastermind.experiments.metrics import (
    ExperimentSummary,
    GameTrialResult,
    TurnMetric,
    aggregate_experiment,
)
from mastermind.experiments.runner import ExactAIPlayer, ExperimentRunner
from mastermind.observation import Feedback
from mastermind.players.ai import AIPlayer
from mastermind.solver.exact import ExactObjective
from mastermind.solver.heuristic import EntropyHeuristic


def test_single_trial_execution():
    """Verify that a single trial completes, isolates secret, and collects turn metrics."""
    config = GameConfig(num_pegs=3, num_colors=3, allow_repeats=True)
    runner = ExperimentRunner()
    player = AIPlayer(heuristic=EntropyHeuristic(), use_first_guess_canonical=True)

    trial = runner.run_trial(config=config, player=player, seed="trial_test_1", trial_id=1)

    assert trial.trial_id == 1
    assert trial.solved is True
    assert trial.total_turns >= 1
    assert len(trial.secret) == 3
    assert len(trial.turn_metrics) == trial.total_turns
    assert trial.total_nodes > 0
    assert trial.total_elapsed_ms > 0

    # Verify first and last turn metrics
    first_turn = trial.turn_metrics[0]
    assert first_turn.turn == 1
    assert len(first_turn.guess) == 3
    assert first_turn.candidates_remaining <= 27

    last_turn = trial.turn_metrics[-1]
    assert last_turn.feedback.is_solved(3)


def test_exact_ai_player():
    """Verify ExactAIPlayer plays using exact policy and solves small configuration."""
    config = GameConfig(num_pegs=3, num_colors=3, allow_repeats=True)
    runner = ExperimentRunner()
    exact_player = ExactAIPlayer(config=config, objective=ExactObjective.EXPECTED_TOTAL_GUESSES)

    trial = runner.run_trial(config=config, player=exact_player, seed="exact_test_1", trial_id=1)

    assert trial.solved is True
    assert trial.total_turns <= 5
    assert trial.turn_metrics[0].is_exact is True


def test_experiment_aggregation():
    """Verify aggregation calculation for win rates, statistics, and optimality gap."""
    config = GameConfig(num_pegs=3, num_colors=3, allow_repeats=True)
    dummy_turn = TurnMetric(
        turn=1,
        guess=(0, 1, 2),
        feedback=Feedback(exact=3, misplaced=0),
        candidates_remaining=1,
        entropy_bits=2.0,
        nodes_evaluated=10,
        elapsed_time_ms=5.0,
        method_name="TestHeuristic",
        is_exact=False,
    )
    trials = [
        GameTrialResult(
            trial_id=1,
            seed="1",
            secret=(0, 1, 2),
            solved=True,
            total_turns=3,
            total_elapsed_ms=15.0,
            total_nodes=30,
            turn_metrics=(dummy_turn,),
        ),
        GameTrialResult(
            trial_id=2,
            seed="2",
            secret=(1, 2, 0),
            solved=True,
            total_turns=4,
            total_elapsed_ms=20.0,
            total_nodes=40,
            turn_metrics=(dummy_turn,),
        ),
    ]

    summary = aggregate_experiment(
        experiment_name="Test Exp",
        config=config,
        strategy_name="Test Strategy",
        budget_description="Test Budget",
        trials=trials,
        exact_reference_mean=3.0,
    )

    assert summary.num_trials == 2
    assert summary.solve_rate == 1.0
    assert summary.mean_guesses == 3.5
    assert summary.min_guesses == 3
    assert summary.max_guesses == 4
    assert summary.total_nodes_evaluated == 70
    assert summary.mean_nodes_per_game == 35.0
    assert summary.optimality_gap == 0.5


def test_csv_and_jsonl_export(tmp_path: Path):
    """Verify exporting trial, turn, and JSONL data structures."""
    config = GameConfig(num_pegs=3, num_colors=3, allow_repeats=True)
    runner = ExperimentRunner()
    player_factory = lambda: AIPlayer(heuristic=EntropyHeuristic(), use_first_guess_canonical=True)

    summary = runner.run_experiment(
        experiment_name="Export Test",
        config=config,
        player_factory=player_factory,
        strategy_name="Entropy",
        budget_description="Full search",
        seeds=["exp_1", "exp_2"],
    )

    trials_csv = tmp_path / "trials.csv"
    turns_csv = tmp_path / "turns.csv"
    jsonl_file = tmp_path / "experiments.jsonl"
    md_file = tmp_path / "REPORT.md"

    export_trials_to_csv([summary], trials_csv)
    export_turns_to_csv([summary], turns_csv)
    export_to_jsonl([summary], jsonl_file)
    export_markdown_report([summary], md_file)

    assert trials_csv.exists()
    assert turns_csv.exists()
    assert jsonl_file.exists()
    assert md_file.exists()

    # Verify trials CSV content
    with open(trials_csv, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0]["strategy_name"] == "Entropy"
        assert reader[0]["solved"] == "True"

    # Verify turns CSV content
    with open(turns_csv, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) >= 2
        assert "exact_pegs" in reader[0]

    # Verify JSONL content
    with open(jsonl_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["num_trials"] == 2
        assert len(data["trials"]) == 2

    # Verify Markdown report content
    md_content = md_file.read_text(encoding="utf-8")
    assert "Mastermind AI Empirical Evaluation Report" in md_content
    assert "Entropy" in md_content
