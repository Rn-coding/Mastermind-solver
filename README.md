# Mastermind AI: Adaptive Problem Solving & Heuristic Search

An AI system and testbed for Mastermind exploring state-space search, belief-state filtering under hidden information, budget-aware heuristic search, and adversarial game dynamics.

## Features

- **Authoritative Game Engine**: Supports arbitrary code lengths (`num_pegs`), color alphabet sizes (`num_colors`), repetition constraints (`allow_repeats`), and guess limits.
- **Strict Information Boundary**: The environment encapsulates the hidden secret; players and solvers access only public observation histories.
- **Belief-State Reasoning**: Maintains consistent candidate sets and partitions candidate spaces based on feedback outcomes.
- **Flexible Solvers**: From exact search on small instances to bounded expectimax and entropy-based information-gain heuristics.
- **Visual Terminal Dashboard**: Rich TUI interface rendering colored peg tokens, round progression, candidate shrinkage, and search telemetry.
- **Adversarial Setter**: Optional mode challenging the solver against an adversarial oracle providing worst-case consistent feedback.

## Installation

Requirements: Python 3.10+

```bash
git clone https://github.com/Rn-coding/mastermind-ai.git
cd mastermind-ai
pip install -e .
pip install pytest
```

## Running the Game

Launch the interactive terminal dashboard:

```bash
mastermind
# or
python -m mastermind.ui.app
```

## Running Tests

Execute the unit and integration test suite:

```bash
pytest
```

## Project Structure

```
mastermind-ai/
├── pyproject.toml
├── README.md
├── src/
│   └── mastermind/
│       ├── config.py          # Configuration schema & validation
│       ├── observation.py     # Public observation contracts & feedback
│       ├── rules.py           # Core game logic & feedback algorithms
│       ├── environment.py     # Authoritative game environment
│       ├── setters/           # Secret generation strategies
│       │   ├── base.py
│       │   └── fixed.py
│       ├── players/           # Human & AI player interfaces
│       ├── solver/            # Search algorithms & belief-state manager
│       └── ui/                # Rich terminal UI & dashboards
└── tests/                     # Test suites
```
