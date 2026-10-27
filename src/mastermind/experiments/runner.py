"""Evaluation runner, experiment orchestrator, and benchmarking CLI."""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Union

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
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
from mastermind.observation import Code, Observation
from mastermind.players.ai import AIPlayer
from mastermind.players.base import BasePlayer
from mastermind.setters.fixed import KnownFixedSetter, RandomFixedSetter
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.budget import SearchBudget
from mastermind.solver.candidates import GuessFilterPolicy
from mastermind.solver.exact import ExactObjective, ExactPolicySolver
from mastermind.solver.heuristic import (
    AnytimeEntropyHeuristic,
    BaseHeuristic,
    EntropyHeuristic,
    ExpectedSizeHeuristic,
    KnuthMinimaxHeuristic,
    MostPartsHeuristic,
)


class ExactAIPlayer(BasePlayer):
    """Player adapter using ExactPolicySolver for small configurations."""

    def __init__(
        self,
        config: GameConfig,
        name: str = "Exact Optimal Policy",
        objective: ExactObjective = ExactObjective.EXPECTED_TOTAL_GUESSES,
        filter_policy: GuessFilterPolicy = GuessFilterPolicy.ALL_LEGAL_CODES,
    ) -> None:
        self._name = name
        self._config = config
        self._solver = ExactPolicySolver(config, objective=objective, filter_policy=filter_policy)
        self._belief_state: Optional[BeliefState] = None
        self._last_result = None

    @property
    def last_result(self):
        return self._last_result

    @property
    def belief_state(self) -> Optional[BeliefState]:
        return self._belief_state

    def get_name(self) -> str:
        return self._name

    def choose_guess(self, observation: Observation) -> Sequence[int]:
        if self._belief_state is None:
            self._belief_state = BeliefState(observation.config)
        self._belief_state.update_from_observation(observation)
        result = self._solver.solve(self._belief_state)
        self._last_result = result
        return result.guess


class ExperimentRunner:
    """Orchestrates individual trials and multi-strategy evaluation suites."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def run_trial(
        self,
        config: GameConfig,
        player: BasePlayer,
        secret: Optional[Code] = None,
        seed: Optional[Union[int, str]] = None,
        trial_id: int = 1,
    ) -> GameTrialResult:
        """Execute one complete Mastermind match and collect turn-by-turn metrics."""
        if secret is not None:
            setter = KnownFixedSetter(secret=secret)
        else:
            setter = RandomFixedSetter(seed=seed)
        env = MastermindEnvironment(config=config, setter=setter)

        turn_metrics: List[TurnMetric] = []
        total_elapsed_ms = 0.0
        total_nodes = 0

        obs = env.get_observation()
        while not obs.is_terminal:
            # Measure solver decision latency
            t0 = time.perf_counter()
            guess_seq = player.choose_guess(obs)
            t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

            guess: Code = tuple(guess_seq)
            turn_result = env.submit_guess(guess)
            obs = env.get_observation()

            # Inspect solver telemetry
            last_result = getattr(player, "last_result", None)
            telemetry = last_result.telemetry if last_result else None

            nodes = telemetry.nodes_evaluated if telemetry else 1
            entropy = (
                abs(telemetry.best_score)
                if (telemetry and "Entropy" in telemetry.method_name)
                else 0.0
            )
            method = telemetry.method_name if telemetry else player.get_name()
            is_exact = telemetry.is_exact if telemetry else False

            # Update belief state to record remaining candidates after feedback
            player_bs = getattr(player, "belief_state", None)
            if player_bs is not None:
                player_bs.update_from_observation(obs)
                cands_remaining = player_bs.size
            else:
                cands_remaining = 1 if obs.is_solved else 0

            total_elapsed_ms += t_elapsed_ms
            total_nodes += nodes

            turn_metrics.append(
                TurnMetric(
                    turn=turn_result.turn,
                    guess=turn_result.guess,
                    feedback=turn_result.feedback,
                    candidates_remaining=cands_remaining,
                    entropy_bits=entropy,
                    nodes_evaluated=nodes,
                    elapsed_time_ms=t_elapsed_ms,
                    method_name=method,
                    is_exact=is_exact,
                )
            )

        secret_revealed = env.reveal_secret(force=True)
        return GameTrialResult(
            trial_id=trial_id,
            seed=seed,
            secret=secret_revealed or (),
            solved=obs.is_solved,
            total_turns=obs.turn_number,
            total_elapsed_ms=total_elapsed_ms,
            total_nodes=total_nodes,
            turn_metrics=tuple(turn_metrics),
        )

    def run_experiment(
        self,
        experiment_name: str,
        config: GameConfig,
        player_factory: Callable[[], BasePlayer],
        strategy_name: str,
        budget_description: str,
        seeds: Sequence[Union[int, str]],
        exact_reference_mean: Optional[float] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> ExperimentSummary:
        """Run a batch of trials under a single strategy and aggregate results."""
        trials: List[GameTrialResult] = []
        total = len(seeds)

        for i, s in enumerate(seeds, 1):
            player = player_factory()
            trial_result = self.run_trial(
                config=config,
                player=player,
                seed=s,
                trial_id=i,
            )
            trials.append(trial_result)
            if on_progress:
                on_progress(i, total)

        return aggregate_experiment(
            experiment_name=experiment_name,
            config=config,
            strategy_name=strategy_name,
            budget_description=budget_description,
            trials=trials,
            exact_reference_mean=exact_reference_mean,
        )

    def run_matrix_suite(
        self,
        seeds: Sequence[Union[int, str]],
        config: Optional[GameConfig] = None,
    ) -> List[ExperimentSummary]:
        """Compare all primary heuristics and strategy selectors on standard Mastermind."""
        cfg = config or GameConfig(num_pegs=4, num_colors=6, allow_repeats=True)
        summaries: List[ExperimentSummary] = []

        strategies: List[Tuple[str, str, Callable[[], BasePlayer]]] = [
            (
                "Shannon Entropy",
                "Full candidate entropy maximization",
                lambda: AIPlayer(
                    name="Entropy AI",
                    heuristic=EntropyHeuristic(),
                    use_first_guess_canonical=True,
                ),
            ),
            (
                "Knuth Minimax",
                "Worst-case remaining candidate minimization",
                lambda: AIPlayer(
                    name="Knuth AI",
                    heuristic=KnuthMinimaxHeuristic(),
                    use_first_guess_canonical=True,
                ),
            ),
            (
                "Irving Expected Size",
                "Expected candidate partition size minimization",
                lambda: AIPlayer(
                    name="Irving AI",
                    heuristic=ExpectedSizeHeuristic(),
                    use_first_guess_canonical=True,
                ),
            ),
            (
                "Most Parts",
                "Partition count maximization",
                lambda: AIPlayer(
                    name="Most Parts AI",
                    heuristic=MostPartsHeuristic(),
                    use_first_guess_canonical=True,
                ),
            ),
            (
                "Adaptive Strategy Selector",
                "Expectimax (< 36 cands) + Anytime Entropy",
                lambda: AIPlayer(
                    name="Adaptive AI",
                    use_strategy_selector=True,
                    budget=SearchBudget(max_time_seconds=0.5),
                    use_first_guess_canonical=True,
                ),
            ),
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            for name, desc, factory in strategies:
                task_id = progress.add_task(f"Running {name} ({len(seeds)} trials)...", total=len(seeds))
                summary = self.run_experiment(
                    experiment_name="Strategy Matrix Comparison",
                    config=cfg,
                    player_factory=factory,
                    strategy_name=name,
                    budget_description=desc,
                    seeds=seeds,
                    on_progress=lambda current, total: progress.update(task_id, completed=current),
                )
                summaries.append(summary)

        return summaries

    def run_scaling_suite(
        self,
        seeds_per_config: Sequence[Union[int, str]],
    ) -> List[ExperimentSummary]:
        """Evaluate how problem complexity scales across board dimensions."""
        configs = [
            ("Small 3p/4c", GameConfig(num_pegs=3, num_colors=4, allow_repeats=True)),
            ("Standard 4p/6c", GameConfig(num_pegs=4, num_colors=6, allow_repeats=True)),
            ("Expanded 5p/6c", GameConfig(num_pegs=5, num_colors=6, allow_repeats=True)),
            ("Wide 4p/8c", GameConfig(num_pegs=4, num_colors=8, allow_repeats=True)),
            ("Distinct 5p/8c", GameConfig(num_pegs=5, num_colors=8, allow_repeats=False)),
        ]

        summaries: List[ExperimentSummary] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            for label, cfg in configs:
                task_id = progress.add_task(f"Scaling {label}...", total=len(seeds_per_config))
                summary = self.run_experiment(
                    experiment_name="Board Scaling Analysis",
                    config=cfg,
                    player_factory=lambda: AIPlayer(
                        name="Entropy AI",
                        heuristic=AnytimeEntropyHeuristic(),
                        budget=SearchBudget(max_time_seconds=1.0),
                        use_first_guess_canonical=True,
                    ),
                    strategy_name=f"Anytime Entropy ({label})",
                    budget_description="1.0s max turn budget, canonical first guess",
                    seeds=seeds_per_config,
                    on_progress=lambda current, total: progress.update(task_id, completed=current),
                )
                summaries.append(summary)

        return summaries

    def run_budget_suite(
        self,
        seeds: Sequence[Union[int, str]],
        config: Optional[GameConfig] = None,
    ) -> List[ExperimentSummary]:
        """Analyze the impact of search deadlines on guess count and node expansion.

        Uses canonical first guess on all budget levels so that deadline is the
        only variable — differences in turn 1 choice do not confound the results.
        """
        cfg = config or GameConfig(num_pegs=4, num_colors=6, allow_repeats=True)
        # Extended budget range: from barely-feasible to unconstrained
        time_budgets = [0.01, 0.05, 0.20, 0.50, 1.00]
        summaries: List[ExperimentSummary] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            for t_budget in time_budgets:
                task_id = progress.add_task(f"Budget {t_budget*1000:.0f}ms...", total=len(seeds))
                summary = self.run_experiment(
                    experiment_name="Search Budget Impact",
                    config=cfg,
                    player_factory=lambda b=t_budget: AIPlayer(
                        name=f"Anytime Entropy ({b*1000:.0f}ms)",
                        heuristic=AnytimeEntropyHeuristic(),
                        budget=SearchBudget(max_time_seconds=b),
                        use_first_guess_canonical=True,
                    ),
                    strategy_name=f"Anytime Entropy ({t_budget*1000:.0f}ms limit)",
                    budget_description=f"Anytime entropy with {t_budget*1000:.0f}ms per-turn deadline, canonical first guess",
                    seeds=seeds,
                    on_progress=lambda current, total: progress.update(task_id, completed=current),
                )
                summaries.append(summary)

        return summaries

    def run_exact_optimality_suite(
        self,
        seeds: Sequence[Union[int, str]],
        config: Optional[GameConfig] = None,
    ) -> List[ExperimentSummary]:
        """Measure optimality gap against global game-tree dynamic programming."""
        cfg = config or GameConfig(num_pegs=3, num_colors=3, allow_repeats=True)
        summaries: List[ExperimentSummary] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            # 1. Exact Optimal Game-Tree Search (Ground truth reference)
            t_exact = progress.add_task(f"Running Exact Tree Search ({cfg.num_pegs}p/{cfg.num_colors}c)...", total=len(seeds))
            exact_summary = self.run_experiment(
                experiment_name="Exact Reference Benchmark",
                config=cfg,
                player_factory=lambda: ExactAIPlayer(
                    config=cfg,
                    objective=ExactObjective.EXPECTED_TOTAL_GUESSES,
                ),
                strategy_name="Exact Tree Policy (Optimal DP)",
                budget_description="Exhaustive minimax game-tree policy",
                seeds=seeds,
                on_progress=lambda c, t: progress.update(t_exact, completed=c),
            )
            summaries.append(exact_summary)
            ref_mean = exact_summary.mean_guesses

            # 2. Shannon Entropy vs Reference
            t_entropy = progress.add_task("Evaluating Entropy vs Reference...", total=len(seeds))
            entropy_summary = self.run_experiment(
                experiment_name="Exact Reference Benchmark",
                config=cfg,
                player_factory=lambda: AIPlayer(
                    name="Entropy AI",
                    heuristic=EntropyHeuristic(),
                    use_first_guess_canonical=False,
                ),
                strategy_name="Shannon Entropy",
                budget_description="Greedy information gain",
                seeds=seeds,
                exact_reference_mean=ref_mean,
                on_progress=lambda c, t: progress.update(t_entropy, completed=c),
            )
            summaries.append(entropy_summary)

            # 3. Knuth Minimax vs Reference
            t_knuth = progress.add_task("Evaluating Knuth vs Reference...", total=len(seeds))
            knuth_summary = self.run_experiment(
                experiment_name="Exact Reference Benchmark",
                config=cfg,
                player_factory=lambda: AIPlayer(
                    name="Knuth AI",
                    heuristic=KnuthMinimaxHeuristic(),
                    use_first_guess_canonical=False,
                ),
                strategy_name="Knuth Minimax",
                budget_description="Minimax worst-case partition",
                seeds=seeds,
                exact_reference_mean=ref_mean,
                on_progress=lambda c, t: progress.update(t_knuth, completed=c),
            )
            summaries.append(knuth_summary)

        return summaries


def print_summary_table(summaries: Sequence[ExperimentSummary], console: Console) -> None:
    """Print a Rich table of aggregated results."""
    table = Table(
        title="[bold yellow]Mastermind AI Empirical Results Summary[/bold yellow]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Strategy", style="cyan", no_wrap=True)
    table.add_column("Config", style="white")
    table.add_column("Trials", justify="right")
    table.add_column("Win Rate", justify="right", style="green")
    table.add_column("Mean ± Std", justify="right", style="bold green")
    table.add_column("Min/Max", justify="center")
    table.add_column("Latency (ms)", justify="right")
    table.add_column("Nodes", justify="right")
    table.add_column("Opt Gap", justify="right", style="bold yellow")

    for s in summaries:
        cfg_str = f"{s.config.num_pegs}p/{s.config.num_colors}c (rep={s.config.allow_repeats})"
        win_str = f"{s.solve_rate * 100:.1f}%"
        mean_str = f"{s.mean_guesses:.2f} ± {s.std_guesses:.2f}"
        min_max_str = f"{s.min_guesses} / {s.max_guesses}"
        time_str = f"{s.mean_game_time_ms:.1f}"
        nodes_str = f"{s.mean_nodes_per_game:,.0f}"
        gap_str = f"{s.optimality_gap:+.3f}" if s.optimality_gap is not None else "-"

        table.add_row(
            s.strategy_name,
            cfg_str,
            str(s.num_trials),
            win_str,
            mean_str,
            min_max_str,
            time_str,
            nodes_str,
            gap_str,
        )

    console.print()
    console.print(table)
    console.print()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command-line entry point for running evaluation suites."""
    parser = argparse.ArgumentParser(
        description="Mastermind AI Evaluation Runner & Empirical Benchmark Suite"
    )
    parser.add_argument(
        "--suite",
        choices=["matrix", "scaling", "budget", "exact", "all"],
        default="all",
        help="Experiment suite to run (default: all)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=20,
        help="Number of trials per experiment setting (default: 20)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Directory to save CSV, JSONL, and Markdown reports (default: results)",
    )
    parser.add_argument(
        "--seed-prefix",
        type=str,
        default="exp_seed_",
        help="Seed prefix for deterministic reproducibility",
    )

    args = parser.parse_args(argv)
    console = Console()

    console.print(
        Panel.fit(
            f"[bold green]Mastermind AI Empirical Evaluation[/bold green]\n"
            f"Suite: [cyan]{args.suite}[/cyan] | Trials: [cyan]{args.trials}[/cyan] | "
            f"Output: [cyan]{args.output_dir}[/cyan]",
            border_style="blue",
        )
    )

    runner = ExperimentRunner(console=console)
    seeds = [f"{args.seed_prefix}{i}" for i in range(args.trials)]

    all_summaries: List[ExperimentSummary] = []

    # Run chosen suites
    if args.suite in ("exact", "all"):
        console.print("[bold]Running Exact Reference & Optimality Gap Suite...[/bold]")
        all_summaries.extend(runner.run_exact_optimality_suite(seeds=seeds[: min(15, len(seeds))]))

    if args.suite in ("matrix", "all"):
        console.print("[bold]Running Strategy Matrix Suite (Knuth, Entropy, Irving, Most Parts)...[/bold]")
        all_summaries.extend(runner.run_matrix_suite(seeds=seeds))

    if args.suite in ("scaling", "all"):
        console.print("[bold]Running Board Complexity Scaling Suite...[/bold]")
        all_summaries.extend(runner.run_scaling_suite(seeds_per_config=seeds[: min(10, len(seeds))]))

    if args.suite in ("budget", "all"):
        console.print("[bold]Running Search Budget & Latency Tradeoff Suite...[/bold]")
        all_summaries.extend(runner.run_budget_suite(seeds=seeds[: min(10, len(seeds))]))

    # Print summary table
    print_summary_table(all_summaries, console)

    # Export artifacts
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_trials_path = export_trials_to_csv(all_summaries, out_dir / "trials.csv")
    csv_turns_path = export_turns_to_csv(all_summaries, out_dir / "turns.csv")
    jsonl_path = export_to_jsonl(all_summaries, out_dir / "experiments.jsonl")
    report_path = export_markdown_report(all_summaries, out_dir / "REPORT.md")

    console.print(f"[bold green]Artifacts successfully saved to {out_dir}/:[/bold green]")
    console.print(f"  • Trials CSV: [cyan]{csv_trials_path}[/cyan]")
    console.print(f"  • Turns CSV:  [cyan]{csv_turns_path}[/cyan]")
    console.print(f"  • JSONL Logs: [cyan]{jsonl_path}[/cyan]")
    console.print(f"  • Markdown:   [cyan]{report_path}[/cyan]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
