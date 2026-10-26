"""Test programmatic play loop using the Stage 1 engine."""

from mastermind.config import GameConfig
from mastermind.environment import MastermindEnvironment
from mastermind.setters.fixed import KnownFixedSetter


def test_scripted_game_play_loop():
    config = GameConfig(num_pegs=4, num_colors=6, max_guesses=5)
    secret = (2, 0, 5, 1)
    setter = KnownFixedSetter(secret=secret, config=config)
    env = MastermindEnvironment(config=config, setter=setter)

    guesses = [
        (0, 1, 2, 3),
        (2, 0, 1, 5),
        (2, 0, 5, 1),
    ]

    for guess in guesses:
        assert not env.is_terminal
        result = env.submit_guess(guess)
        if result.is_solved:
            break

    obs = env.get_observation()
    assert obs.is_solved is True
    assert obs.is_terminal is True
    assert obs.turn_number == 3
    assert len(obs.history) == 3
    assert env.reveal_secret() == secret
