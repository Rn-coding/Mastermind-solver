"""Interactive terminal application for playing Mastermind."""

from __future__ import annotations
import sys
from typing import Optional, Tuple
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
from mastermind.players.human import HumanPlayer
from mastermind.setters.fixed import RandomFixedSetter
from mastermind.ui.formatters import parse_guess_input
from mastermind.ui.game_view import render_board, render_color_legend, render_header, render_status


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
        seed = int(seed_str) if seed_str.isdigit() else None

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

    def prompt_human_guess(self, env: MastermindEnvironment) -> Optional[Tuple[int, ...]]:
        """Prompt user for a guess, allowing in-game commands like help or quit."""
        obs = env.get_observation()
        config = obs.config

        while True:
            prompt_label = (
                f"[bold cyan]Turn {obs.turn_number + 1}[/bold cyan] "
                f"Enter {config.num_pegs} pegs (or '?' for help, 'quit' to exit)"
            )
            raw = Prompt.ask(prompt_label, console=self.console).strip()

            if not raw:
                continue

            cmd = raw.lower()
            if cmd in ("quit", "exit", "q"):
                return None
            if cmd in ("?", "help"):
                self.console.print(render_color_legend(config))
                continue
            if cmd == "board":
                self.console.print(render_board(obs))
                continue

            try:
                guess = parse_guess_input(raw, config)
                return guess
            except ValueError as err:
                self.console.print(f"[bold red]Invalid guess:[/] {err}")
                self.console.print("[dim]Tip: Use integers (e.g. '0 1 2 3') or letters (e.g. 'R G B Y')[/dim]")

    def play_game(self, config: Optional[GameConfig] = None) -> bool:
        """Run a single game match to completion.

        Returns:
            True if the player wants to play another game, False to exit.
        """
        if config is None:
            config = self.select_configuration()

        setter = RandomFixedSetter(seed=config.seed)
        env = MastermindEnvironment(config=config, setter=setter)

        self.console.clear()
        self.console.print(render_header(config))
        self.console.print(render_color_legend(config))
        self.console.print(render_board(env.get_observation()))

        while not env.is_terminal:
            guess = self.prompt_human_guess(env)
            if guess is None:
                self.console.print("[yellow]Game aborted by player.[/yellow]")
                break

            result = env.submit_guess(guess)
            obs = env.get_observation()

            self.console.clear()
            self.console.print(render_header(config))
            self.console.print(render_color_legend(config))
            self.console.print(render_board(obs))
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
