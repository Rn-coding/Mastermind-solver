"""Simple command-line driver demonstrating a playable Mastermind game without an AI solver."""

from __future__ import annotations
import sys
from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
from mastermind.setters.fixed import RandomFixedSetter


def run_cli_game(seed: int = 42) -> None:
    """Run an interactive terminal game loop."""
    config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=True, max_guesses=10, seed=seed)
    setter = RandomFixedSetter(seed=config.seed)
    env = MastermindEnvironment(config=config, setter=setter)

    print("=" * 60)
    print("Welcome to Mastermind (Stage 1 Engine Demo)")
    print(f"Rules: {config.num_pegs} pegs, {config.num_colors} colors (0 to {config.num_colors - 1}).")
    print(f"Repeats allowed: {config.allow_repeats}. Max turns: {config.max_guesses}.")
    print("=" * 60)

    obs = env.get_observation()
    while not obs.is_terminal:
        print(f"\n--- Turn {obs.turn_number + 1} of {config.max_guesses} ---")
        prompt = f"Enter {config.num_pegs} space-separated integers in [0, {config.num_colors - 1}]: "
        try:
            line = input(prompt).strip()
            if not line:
                continue
            guess = tuple(int(x) for x in line.split())
        except (ValueError, EOFError):
            print("Invalid input format. Example: 0 1 2 3")
            continue

        try:
            res = env.submit_guess(guess)
        except ValueError as err:
            print(f"Invalid guess: {err}")
            continue

        print(f"Feedback -> Exact (black pegs): {res.feedback.exact}, Misplaced (white pegs): {res.feedback.misplaced}")
        obs = env.get_observation()

    print("\n" + "=" * 60)
    if obs.is_solved:
        print(f"Congratulations! You solved the code in {obs.turn_number} turn(s)!")
    else:
        print("Game Over: Max guesses reached.")

    # Reveal secret now that the game is terminal
    print(f"Secret code was: {env.reveal_secret()}")
    print("=" * 60)


if __name__ == "__main__":
    seed_val = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    run_cli_game(seed=seed_val)
