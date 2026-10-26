"""Tests for Mastermind rules, code validation, and feedback calculations."""

import pytest
from mastermind.config import GameConfig
from mastermind.rules import calculate_feedback, generate_all_codes, validate_code


class TestGameConfig:
    def test_default_config_is_valid(self):
        config = GameConfig()
        assert config.num_pegs == 4
        assert config.num_colors == 6
        assert config.allow_repeats is True
        assert config.max_guesses == 10

    def test_invalid_num_pegs(self):
        with pytest.raises(ValueError, match="num_pegs"):
            GameConfig(num_pegs=0)

    def test_invalid_num_colors(self):
        with pytest.raises(ValueError, match="num_colors"):
            GameConfig(num_colors=0)

    def test_no_repeats_pigeonhole_validation(self):
        # 5 pegs with only 4 colors cannot exist without repetition
        with pytest.raises(ValueError, match="cannot exceed num_colors"):
            GameConfig(num_pegs=5, num_colors=4, allow_repeats=False)

    def test_invalid_max_guesses(self):
        with pytest.raises(ValueError, match="max_guesses"):
            GameConfig(max_guesses=0)


class TestCodeValidation:
    def test_valid_code(self):
        config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=True)
        # Should not raise
        validate_code((0, 1, 2, 3), config)
        validate_code((0, 0, 5, 5), config)

    def test_code_length_mismatch(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        with pytest.raises(ValueError, match="Code length mismatch"):
            validate_code((0, 1, 2), config)
        with pytest.raises(ValueError, match="Code length mismatch"):
            validate_code((0, 1, 2, 3, 4), config)

    def test_color_out_of_bounds(self):
        config = GameConfig(num_pegs=4, num_colors=6)
        with pytest.raises(ValueError, match="must be an integer in range"):
            validate_code((0, 1, 6, 2), config)
        with pytest.raises(ValueError, match="must be an integer in range"):
            validate_code((-1, 1, 2, 3), config)

    def test_repeats_disallowed(self):
        config = GameConfig(num_pegs=4, num_colors=6, allow_repeats=False)
        with pytest.raises(ValueError, match="duplicate colors"):
            validate_code((0, 1, 2, 0), config)


class TestCodeGeneration:
    def test_generate_with_repeats(self):
        config = GameConfig(num_pegs=3, num_colors=4, allow_repeats=True)
        codes = generate_all_codes(config)
        # 4^3 = 64
        assert len(codes) == 64
        assert len(set(codes)) == 64
        for code in codes:
            assert len(code) == 3
            assert all(0 <= peg < 4 for peg in code)

    def test_generate_without_repeats(self):
        config = GameConfig(num_pegs=3, num_colors=5, allow_repeats=False)
        codes = generate_all_codes(config)
        # P(5, 3) = 5 * 4 * 3 = 60
        assert len(codes) == 60
        assert len(set(codes)) == 60
        for code in codes:
            assert len(set(code)) == 3


class TestFeedbackCalculation:
    def test_all_exact_match(self):
        secret = (1, 2, 3, 4)
        guess = (1, 2, 3, 4)
        fb = calculate_feedback(secret, guess)
        assert fb.exact == 4
        assert fb.misplaced == 0
        assert fb.is_solved(4) is True

    def test_no_matches_at_all(self):
        secret = (0, 1, 2, 3)
        guess = (4, 5, 4, 5)
        fb = calculate_feedback(secret, guess)
        assert fb.exact == 0
        assert fb.misplaced == 0
        assert fb.is_solved(4) is False

    def test_all_misplaced_derangement(self):
        secret = (0, 1, 2, 3)
        guess = (1, 2, 3, 0)
        fb = calculate_feedback(secret, guess)
        assert fb.exact == 0
        assert fb.misplaced == 4

    @pytest.mark.parametrize(
        "secret,guess,expected_exact,expected_misplaced",
        [
            # Classic repeated-color Mastermind scenarios:
            ((1, 1, 2, 3), (1, 2, 1, 4), 1, 2),
            ((1, 1, 2, 2), (1, 1, 1, 1), 2, 0),
            ((0, 0, 1, 1), (0, 1, 0, 1), 2, 2),
            ((0, 1, 0, 1), (1, 0, 1, 0), 0, 4),
            ((2, 2, 2, 2), (2, 3, 2, 3), 2, 0),
            ((0, 1, 2, 3), (0, 0, 0, 0), 1, 0),
            ((0, 0, 0, 1), (2, 0, 0, 0), 2, 1),
            ((3, 3, 1, 2), (3, 1, 3, 4), 1, 2),
            ((1, 2, 3), (3, 2, 1), 1, 2),
            ((0, 1, 2), (1, 2, 0), 0, 3),
            ((5,), (5,), 1, 0),
            ((5,), (4,), 0, 0),
        ],
    )
    def test_feedback_repeated_colors_cases(
        self, secret, guess, expected_exact, expected_misplaced
    ):
        fb = calculate_feedback(secret, guess)
        assert fb.exact == expected_exact
        assert fb.misplaced == expected_misplaced

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="Length mismatch"):
            calculate_feedback((1, 2, 3), (1, 2, 3, 4))
