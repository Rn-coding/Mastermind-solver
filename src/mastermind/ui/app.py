"""Interactive terminal application for playing Mastermind."""

from __future__ import annotations
import sys
import time
from typing import Optional, Tuple
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
from mastermind.players.ai import AIPlayer
from mastermind.players.human import HumanPlayer
from mastermind.setters.fixed import RandomFixedSetter
from mastermind.solver.belief_state import BeliefState
from mastermind.solver.budget import SearchBudget
from mastermind.solver.candidates import CandidateGenerator, GuessFilterPolicy
from mastermind.solver.heuristic import (
    AnytimeEntropyHeuristic,
    AsyncAnytimeWorker,
    analyze_guess_partitions,
)
from mastermind.ui.formatters import parse_guess_input
from mastermind.ui.game_view import (
    render_ai_hint,
    render_board,
    render_candidate_inspection,
    render_color_legend,
    render_detailed_guess_eval,
    render_header,
    render_interactive_help,
    render_status,
    render_telemetry_panel,
    render_top_guesses_table,
)


PRESETS = {
    "1": ("Standard (4 pegs, 6 colors, 10 guesses)", GameConfig(num_pegs=4, num_colors=6, allow_repeats=True, max_guesses=10)),
    "2": ("Quick / Beginner (3 pegs, 4 colors, 8 guesses)", GameConfig(num_pegs=3, num_colors=4, allow_repeats=True, max_guesses=8)),
    "3": ("Master / Expert (5 pegs, 8 colors, 12 guesses)", GameConfig(num_pegs=5, num_colors=8, allow_repeats=True, max_guesses=12)),
    "4": ("No-Repeats Challenge (4 pegs, 6 colors, no repeats, 10 guesses)", GameConfig(num_pegs=4, num_colors=6, allow_repeats=False, max_guesses=10)),
}


class MastermindApp:
    """Modern terminal application managing game UI lifecycle and human play."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.ai_timeline: float = 2.0

    def select_configuration(self) -> GameConfig:
        """Prompt user to select a preset configuration or build a custom one."""
        self.console.print("\n[bold bright_cyan]Select Game Difficulty / Preset:[/bold bright_cyan]")
        for key, (label, _) in PRESETS.items():
            self.console.print(f"  [bold yellow]{key}[/bold yellow]: {label}")
        self.console.print("  [bold yellow]5[/bold yellow]: Custom Configuration")

        choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4", "5"], default="1", console=self.console)

        if choice in PRESETS:
            return PRESETS[choice][1]

        # Custom configuration builder
        self.console.print("\n[bold bright_yellow]--- Custom Game Setup ---[/bold bright_yellow]")
        num_pegs = IntPrompt.ask("Number of pegs", default=4, console=self.console)
        num_colors = IntPrompt.ask("Number of colors (max 10 recommended)", default=6, console=self.console)
        allow_repeats = Confirm.ask("Allow repeated colors?", default=True, console=self.console)
        max_guesses_in = IntPrompt.ask("Max guesses allowed (0 for unlimited)", default=10, console=self.console)
        max_guesses = max_guesses_in if max_guesses_in > 0 else None

        seed_str = Prompt.ask("Random seed for secret (leave blank for random)", default="", console=self.console).strip()
        seed = int(seed_str) if seed_str.isdigit() else (seed_str if seed_str else None)

        try:
            return GameConfig(
                num_pegs=num_pegs,
                num_colors=num_colors,
                allow_repeats=allow_repeats,
                max_guesses=max_guesses,
                seed=seed,
            )
        except ValueError as err:
            self.console.print(f"[bold red]Configuration error:[/] {err}. Using Standard preset.")
            return PRESETS["1"][1]

    def handle_interactive_command(
        self,
        cmd: str,
        env: MastermindEnvironment,
        belief_state: BeliefState,
    ) -> bool:
        """Process non-guess interactive commands like hint, eval, inspect, timeline.

        Returns:
            True if the command was recognized and handled, False otherwise.
        """
        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""
        config = env.config

        if action in ("?", "help"):
            self.console.print(render_interactive_help())
            self.console.print(render_color_legend(config))
            return True

        if action == "board":
            self.console.print(render_board(env.get_observation()))
            return True

        if action in ("inspect", "state"):
            self.console.print(render_candidate_inspection(belief_state, config))
            return True

        if action in ("hint", "h"):
            with self.console.status(f"[bold yellow]AI evaluating belief state (timeline {self.ai_timeline:.1f}s)...[/bold yellow]"):
                heuristic = AnytimeEntropyHeuristic(timeline_seconds=self.ai_timeline)
                cand_gen = CandidateGenerator(config)
                guesses = cand_gen.generate_candidate_guesses(belief_state)
                result = heuristic.select_best_guess(guesses, belief_state)
            self.console.print(render_ai_hint(result, config))
            return True

        if action == "eval":
            if not args:
                self.console.print("[bold red]Usage:[/] eval <guess> (e.g. 'eval 0 1 2 3' or 'eval R G B Y')")
                return True
            try:
                eval_guess = parse_guess_input(args, config)
                with self.console.status("[bold cyan]Computing feedback partition distribution and entropy...[/bold cyan]"):
                    analysis = analyze_guess_partitions(eval_guess, belief_state)
                self.console.print(render_detailed_guess_eval(analysis, config))
            except ValueError as err:
                self.console.print(f"[bold red]Cannot evaluate guess:[/] {err}")
            return True

        if action == "top":
            count = 5
            if args.isdigit():
                count = max(1, min(20, int(args)))
            with self.console.status(f"[bold cyan]Evaluating top {count} candidate guesses...[/bold cyan]"):
                heuristic = AnytimeEntropyHeuristic(timeline_seconds=self.ai_timeline)
                cand_gen = CandidateGenerator(config)
                guesses = cand_gen.generate_candidate_guesses(belief_state)
                res = heuristic.select_best_guess(guesses, belief_state)
            self.console.print(render_top_guesses_table(res.telemetry.top_guesses[:count], config))
            return True

        if action in ("timeline", "budget"):
            if not args:
                self.console.print(f"[bold cyan]Current AI search timeline:[/] {self.ai_timeline:.1f} seconds per decision.")
                return True
            try:
                new_time = float(args)
                if new_time <= 0:
                    self.console.print("[bold red]Timeline must be positive.[/bold red]")
                else:
                    self.ai_timeline = new_time
                    self.console.print(f"[bold green]AI search timeline updated to {self.ai_timeline:.1f}s.[/bold green]")
            except ValueError:
                self.console.print("[bold red]Invalid number for timeline. Example: 'timeline 2.5'[/bold red]")
            return True

        return False

    def prompt_human_guess(
        self,
        env: MastermindEnvironment,
        belief_state: BeliefState,
    ) -> Optional[Tuple[int, ...]]:
        """Prompt user for a guess, handling interactive analysis commands."""
        obs = env.get_observation()
        config = obs.config

        while True:
            prompt_label = (
                f"[bold cyan]Turn {obs.turn_number + 1}[/bold cyan] "
                f"Enter {config.num_pegs} pegs (or 'hint', 'eval', 'inspect', 'help', 'q')"
            )
            raw = Prompt.ask(prompt_label, console=self.console).strip()

            if not raw:
                continue

            if raw.lower() in ("quit", "exit", "q"):
                return None

            if self.handle_interactive_command(raw, env, belief_state):
                continue

            try:
                guess = parse_guess_input(raw, config)
                return guess
            except ValueError as err:
                self.console.print(f"[bold red]Invalid guess:[/] {err}")
                self.console.print("[dim]Tip: Use integers (e.g. '0 1 2 3') or letters (e.g. 'R G B Y'), or 'hint' for advice[/dim]")

    def select_game_mode(self) -> str:
        """Prompt user to select between Human play, AI autoplay, or AI step-mode."""
        self.console.print("\n[bold bright_cyan]Select Gameplay Mode:[/bold bright_cyan]")
        self.console.print("  [bold yellow]1[/bold yellow]: Human Player (Crack the code yourself)")
        self.console.print("  [bold yellow]2[/bold yellow]: AI Autoplay (Watch adaptive AI solve the code)")
        self.console.print("  [bold yellow]3[/bold yellow]: AI Step-by-Step (Inspect AI decision telemetry each turn)")

        return Prompt.ask("Choose mode", choices=["1", "2", "3"], default="1", console=self.console)

    def play_game(self, config: Optional[GameConfig] = None) -> bool:
        """Run a single game match to completion.

        Returns:
            True if the player wants to play another game, False to exit.
        """
        mode = self.select_game_mode()

        if config is None:
            config = self.select_configuration()

        setter = RandomFixedSetter(seed=config.seed)
        env = MastermindEnvironment(config=config, setter=setter)
        belief_state = BeliefState(config)

        ai_player: Optional[AIPlayer] = None
        if mode in ("2", "3"):
            ai_player = AIPlayer(
                use_strategy_selector=True,
                budget=SearchBudget(max_time_seconds=self.ai_timeline),
            )

        self.console.clear()
        self.console.print(render_header(config))
        self.console.print(render_color_legend(config))
        self.console.print(render_board(env.get_observation()))

        while not env.is_terminal:
            if ai_player is not None:
                if mode == "3":
                    obs = env.get_observation()
                    if obs.turn_number == 0 and ai_player._use_first_guess_canonical:
                        guess = ai_player.choose_guess(obs)
                    else:
                        cand_gen = CandidateGenerator(config)
                        guesses = cand_gen.generate_candidate_guesses(
                            belief_state,
                            policy=GuessFilterPolicy.ALL_LEGAL_CODES,
                            max_guesses=ai_player._budget.max_candidate_guesses,
                        )
                        heuristic = AnytimeEntropyHeuristic(
                            timeline_seconds=self.ai_timeline,
                            max_memory_mb=ai_player._budget.max_memory_mb or 512.0,
                        )
                        # Launch asynchronous background search immediately
                        worker = AsyncAnytimeWorker(
                            heuristic=heuristic,
                            guesses=guesses,
                            belief_state=belief_state,
                            timeline_seconds=self.ai_timeline,
                        )
                        self.console.print(
                            f"[dim cyan]AI is evaluating candidates in the background (timeline {self.ai_timeline:.1f}s)...[/dim cyan]"
                        )

                        while True:
                            status_tag = "[bold green]Ready[/]" if worker.is_finished else "[yellow]Computing...[/]"
                            prompt_label = (
                                f"[bold cyan]Turn {env.turn_number + 1}[/bold cyan] ({status_tag}) "
                                f"Press Enter to play move (or 'eval', 'inspect', 'timeline <sec>', 'top', 'q')"
                            )
                            step = Prompt.ask(prompt_label, default="", console=self.console).strip()
                            if not step:
                                result_obj = worker.stop_and_get_result()
                                guess = result_obj.guess
                                ai_player._last_result = result_obj
                                break
                            if step.lower() in ("q", "quit", "exit"):
                                worker.stop_and_get_result()
                                self.console.print("[yellow]AI session aborted by user.[/yellow]")
                                return False
                            if self.handle_interactive_command(step, env, belief_state):
                                ai_player._budget.max_time_seconds = self.ai_timeline
                                continue
                            self.console.print("[dim]Press Enter to proceed with AI move, or type 'help'[/dim]")
                else:
                    time.sleep(0.4)
                    obs = env.get_observation()
                    guess = ai_player.choose_guess(obs)
            else:
                guess = self.prompt_human_guess(env, belief_state)
                if guess is None:
                    self.console.print("[yellow]Game aborted by player.[/yellow]")
                    break

            result = env.submit_guess(guess)
            obs = env.get_observation()
            belief_state.update_from_observation(obs)

            self.console.clear()
            self.console.print(render_header(config))
            self.console.print(render_color_legend(config))
            self.console.print(render_board(obs))

            # Display AI Telemetry if available
            if ai_player and ai_player.last_result:
                self.console.print(render_telemetry_panel(ai_player.last_result.telemetry))

            self.console.print(render_status(obs, secret=env.reveal_secret() if obs.is_terminal else None))

        # Game ended
        if env.is_terminal:
            play_again = Confirm.ask("\nWould you like to play again?", default=True, console=self.console)
            return play_again

        return False

    def run(self) -> None:
        """Main entry point loop for the application."""
        self.console.print(render_header(GameConfig(), title="WELCOME TO MASTERMIND AI"))
        while True:
            want_replay = self.play_game()
            if not want_replay:
                self.console.print("\n[bold cyan]Thanks for playing Mastermind! Goodbye![/bold cyan]")
                break


def main() -> None:
    """CLI script entrypoint."""
    app = MastermindApp()
    try:
        app.run()
    except (KeyboardInterrupt, EOFError):
        app.console.print("\n[dim]Session terminated.[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
