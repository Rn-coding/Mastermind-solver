"""Tests for Mastermind code setter implementations."""

import pytest
from mastermind.config import GameConfig
from mastermind.rules import validate_code
from mastermind.setters.fixed import KnownFixedSetter, RandomFixedSetter


class TestKnownFixedSetter:
    def test_evaluate_guess(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        setter = KnownFixedSetter(secret=(0, 1, 2, 3), config=config)
        fb = setter.evaluate_guess((0, 1, 4, 5))
        assert fb.exact == 2
        assert fb.misplaced == 0
        assert setter.reveal_secret() == (0, 1, 2, 3)

    def test_invalid_secret_raises(self):
        config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=False)
        with pytest.raises(ValueError):
            KnownFixedSetter(secret=(0, 0, 1, 2), config=config)


class TestRandomFixedSetter:
    def test_deterministic_with_seed(self):
        config = GameConfig(num_pegs=4, num_colors=6, seed=42)
        setter1 = RandomFixedSetter()
        setter1.initialize(config)
        secret1 = setter1.reveal_secret()

        setter2 = RandomFixedSetter(seed=42)
        setter2.initialize(GameConfig(num_pegs=4, num_colors=6))
        secret2 = setter2.reveal_secret()

        assert secret1 == secret2
        validate_code(secret1, config)

    def test_random_setter_without_repeats(self):
        config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=False, seed=99)
        setter = RandomFixedSetter()
        setter.initialize(config)
        secret = setter.reveal_secret()
        assert secret is not None
        assert len(set(secret)) == config.num_pegs
        validate_code(secret, config)

    def test_uninitialized_evaluate_raises(self):
        setter = RandomFixedSetter()
        with pytest.raises(RuntimeError, match="not been initialized"):
            setter.evaluate_guess((0, 1, 2, 3))
