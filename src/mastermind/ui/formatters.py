"""Visual formatting utilities, color palettes, and input parsers for Mastermind."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
from mastermind.config import GameConfig
from mastermind.observation import Code, Feedback


@dataclass(frozen=True)
class ColorTheme:
    """Styling properties for a game color."""

    index: int
    name: str
    letter: str
    rich_style: str
    glyph: str = "●"


PALETTE: List[ColorTheme] = [
    ColorTheme(0, "Red", "R", "bold red"),
    ColorTheme(1, "Green", "G", "bold green"),
    ColorTheme(2, "Blue", "G", "bold deep_sky_blue1"),
    ColorTheme(3, "Yellow", "Y", "bold bright_yellow"),
    ColorTheme(4, "Orange", "O", "bold dark_orange"),
    ColorTheme(5, "Purple", "P", "bold magenta"),
    ColorTheme(6, "Cyan", "C", "bold cyan"),
    ColorTheme(7, "White", "W", "bold white"),
    ColorTheme(8, "Pink", "K", "bold hot_pink"),
    ColorTheme(9, "Brown", "B", "bold tan"),
]

# Ensure distinct single-letter fallback tokens
for idx, item in enumerate(PALETTE):
    if item.letter == "G" and item.name == "Blue":
        PALETTE[idx] = ColorTheme(2, "Blue", "B", "bold deep_sky_blue1")
    elif item.letter == "B" and item.name == "Brown":
        PALETTE[idx] = ColorTheme(9, "Brown", "N", "bold tan")


def get_color_theme(color_idx: int, config: Optional[GameConfig] = None) -> ColorTheme:
    """Retrieve theme properties for a given color index."""
    if color_idx < len(PALETTE):
        base = PALETTE[color_idx]
        if config and config.color_names and color_idx < len(config.color_names):
            name = config.color_names[color_idx]
            return ColorTheme(color_idx, name, name[0].upper(), base.rich_style, base.glyph)
        return base
    # Fallback for large alphabets
    return ColorTheme(
        index=color_idx,
        name=f"Color-{color_idx}",
        letter=str(color_idx % 10),
        rich_style="bold bright_white",
        glyph="●",
    )


def format_peg(color_idx: int, config: Optional[GameConfig] = None, show_label: bool = True) -> str:
    """Render a single colored peg for Rich terminal display."""
    theme = get_color_theme(color_idx, config)
    if show_label:
        return f"[{theme.rich_style}]{theme.glyph} {theme.index}:{theme.name}[/{theme.rich_style}]"
    return f"[{theme.rich_style}]{theme.glyph}[/{theme.rich_style}]"


def format_code(code: Sequence[int], config: Optional[GameConfig] = None, compact: bool = False) -> str:
    """Render a sequence of pegs as a clean visual code row."""
    if compact:
        tokens = [
            f"[{get_color_theme(peg, config).rich_style}]{get_color_theme(peg, config).glyph}[/]"
            for peg in code
        ]
        return " ".join(tokens)
    else:
        tokens = [
            f"[{get_color_theme(peg, config).rich_style}]{get_color_theme(peg, config).glyph} {get_color_theme(peg, config).letter}[/]"
            for peg in code
        ]
        return "  ".join(tokens)


def format_feedback(feedback: Feedback, num_pegs: int) -> str:
    """Render visual feedback pegs: Exact (● red), Misplaced (○ white), and Empty (· dim)."""
    exact_pegs = " ".join(["[bold red]●[/]"] * feedback.exact) if feedback.exact > 0 else ""
    misplaced_pegs = " ".join(["[bold white]○[/]"] * feedback.misplaced) if feedback.misplaced > 0 else ""
    empty_count = max(0, num_pegs - feedback.exact - feedback.misplaced)
    empty_pegs = " ".join(["[dim]·[/]"] * empty_count) if empty_count > 0 else ""

    pegs = " ".join(filter(bool, [exact_pegs, misplaced_pegs, empty_pegs]))
    return f"{pegs}  [dim](Exact: {feedback.exact}, Misplaced: {feedback.misplaced})[/dim]"


def parse_guess_input(raw: str, config: GameConfig) -> Tuple[int, ...]:
    """Parse a user's input string into a valid Code tuple.

    Supports:
      - Space or comma separated integers: "0 1 2 3" or "0, 1, 2, 3"
      - Compact integer string: "0123" (when num_colors <= 10)
      - Letter tokens: "R G B Y" or "RGBY"

    Raises:
        ValueError: On incorrect peg count, invalid color indices, or duplicate colors if forbidden.
    """
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("Input cannot be empty.")

    # Letter mapping
    letter_map: Dict[str, int] = {}
    for i in range(config.num_colors):
        theme = get_color_theme(i, config)
        letter_map[theme.letter.upper()] = i
        letter_map[theme.name.upper()] = i

    tokens: List[int] = []

    # Case 1: Comma-separated or space-separated
    delimiters = [",", " "]
    for delim in delimiters:
        if delim in cleaned:
            parts = [p.strip() for p in cleaned.split(delim) if p.strip()]
            parsed_parts: List[int] = []
            for part in parts:
                if part.isdigit():
                    parsed_parts.append(int(part))
                elif part.upper() in letter_map:
                    parsed_parts.append(letter_map[part.upper()])
                else:
                    raise ValueError(f"Unrecognized color token: '{part}'")
            tokens = parsed_parts
            break

    # Case 2: No delimiter (e.g. "0123" or "RGBY")
    if not tokens:
        if cleaned.isdigit() and len(cleaned) == config.num_pegs:
            tokens = [int(ch) for ch in cleaned]
        elif all(ch.upper() in letter_map for ch in cleaned) and len(cleaned) == config.num_pegs:
            tokens = [letter_map[ch.upper()] for ch in cleaned]
        else:
            # Single integer or unrecognized sequence
            if cleaned.isdigit():
                tokens = [int(cleaned)]
            else:
                raise ValueError(f"Could not parse guess: '{raw}'. Expected {config.num_pegs} pegs.")

    # Validate length
    if len(tokens) != config.num_pegs:
        raise ValueError(f"Expected {config.num_pegs} pegs, but received {len(tokens)}.")

    # Validate color bounds
    for idx, peg in enumerate(tokens):
        if peg < 0 or peg >= config.num_colors:
            raise ValueError(
                f"Color index {peg} at position {idx + 1} is out of bounds (allowed: 0..{config.num_colors - 1})."
            )

    # Validate repeats if prohibited
    if not config.allow_repeats and len(set(tokens)) != len(tokens):
        raise ValueError("Duplicate colors are not permitted in this game configuration.")

    return tuple(tokens)
