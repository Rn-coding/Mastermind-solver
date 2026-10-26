# Mastermind AI: Adaptive Problem Solving & Heuristic Search

An AI problem-solving agent and evaluation testbed for Mastermind built with Python, featuring exact game-tree dynamic programming, information-theoretic heuristics, anytime budget-constrained search, and an interactive terminal user interface (TUI).

Developed for an AI course project in accordance with classical AI problem-solving principles.

---

## 1. Key Highlights & Architectural Principles

- **Strict Secret Encapsulation**: The authoritative game environment ([`MastermindEnvironment`](src/mastermind/environment.py)) encapsulates the hidden code. AI players receive only public [`Observation`](src/mastermind/observation.py) history and never read secret attributes.
- **Deductive Belief-State Reasoning**: Maintains consistent candidate sets across turns. Employs exact permutation generation for compact boards and stochastic CSP min-conflicts local search for large combinatorial state spaces ($> 10^6$).
- **Multi-Paradigm Solver Suite**:
  - **Exact Optimal Search**: Exhaustive game-tree dynamic programming with transposition tables ([`ExactPolicySolver`](src/mastermind/solver/exact.py)) computing theoretical lower bounds.
  - **Information-Theoretic Heuristics**: Shannon Entropy ($H(g) = -\sum p_i \log_2 p_i$), Knuth Minimax ($\min_g \max_f |S_{g,f}|$), Irving Expected Partition Size ($\sum |S|^2 / |C|$), and Most Parts.
  - **Bounded Expectimax**: Multi-ply lookahead with depth and node budgeting ([`BoundedExpectimaxSolver`](src/mastermind/solver/expectimax.py)).
  - **Resource-Aware Anytime Search**: Continuous background evaluation with candidate ranking and graceful early return upon timeline exhaustion ([`AnytimeEntropyHeuristic`](src/mastermind/solver/heuristic.py) & [`AsyncAnytimeWorker`](src/mastermind/solver/heuristic.py)).
  - **Adaptive Strategy Selector**: Automatically profiles candidate space and remaining search budget to route between exact deduction, expectimax, and anytime search ([`StrategySelector`](src/mastermind/solver/strategy_selector.py)).
- **Interactive Terminal UI**: Rich dashboard featuring color peg rendering, candidate shrinkage telemetry, anytime background search, and interactive commands (`hint`, `eval`, `inspect`, `top`, `timeline`).
- **Comprehensive Evaluation Suite**: CLI evaluation harness ([`mastermind-eval`](src/mastermind/experiments/runner.py)) exporting trial and turn CSVs, JSONL logs, and publication-ready Markdown reports.

---

## 2. Installation & Quick Start

### Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### Setup
```bash
# Clone the repository
git clone https://github.com/Rn-coding/Mastermind-solver.git
cd Mastermind-solver

# Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install package in editable mode with development dependencies
pip install -e ".[dev]"
```

---

## 3. Running the Game (Interactive TUI)

Launch the playable game via entry point or Python module:

```bash
mastermind
# or
python -m mastermind.ui.app
```

### Game Modes
1. **Human Play**: Enter guesses as numbers (`0 1 2 3` or `0123`) or letters (`R G B Y`).
2. **AI Autoplay**: Watch the AI systematically eliminate candidates and solve the board in 4–5 turns.
3. **Interactive AI Step Mode**:
   - The AI solver runs in the background. Press `Enter` to proceed with the best evaluated guess, or type interactive commands:
     - `hint`: Recommends the highest-entropy guess with score breakdown.
     - `eval <guess>`: Evaluates any candidate or non-candidate guess (entropy, expected partition size, worst-case size).
     - `inspect <guess>`: Displays the feedback outcome distribution (histogram) across all possible black/white peg combinations.
     - `top [n]`: Shows the top $N$ candidate guesses currently ranked by the solver.
     - `timeline <seconds>`: Dynamically adjusts the AI search timeout for subsequent turns.

---

## 4. Empirical Evaluation Suite (`mastermind-eval`)

The automated evaluation runner benchmarks algorithms against deterministic secret sets without UI overhead:

```bash
# Run all evaluation suites (exact reference, strategy matrix, scaling, budget tradeoff)
mastermind-eval --suite all --trials 20 --output-dir results

# Run specific suite
mastermind-eval --suite matrix --trials 15
mastermind-eval --suite exact --trials 15
mastermind-eval --suite scaling --trials 10
mastermind-eval --suite budget --trials 10
```

### Generated Artifacts
All benchmark runs export structured data into the specified output directory (default: `results/`):
- `results/trials.csv`: Trial-by-trial metrics (seed, secret, total turns, game latency, node count).
- `results/turns.csv`: Granular turn-by-turn trajectory (guess, feedback, candidates remaining, entropy bits, turn latency, solver method).
- `results/experiments.jsonl`: Full structured JSON Lines log including configuration and telemetry.
- `results/REPORT.md`: Aggregated statistical report with Markdown tables and optimality gaps.

---

## 5. Measured Experimental Results

Below are empirical results obtained from running the evaluation suite across standardized configurations (sample size: 10–15 trials per setting, deterministic seeds, secret encapsulation verified):

### 5.1 Strategy Matrix Comparison (Standard $4\text{ pegs}, 6\text{ colors}$)
| Strategy | Mean Guesses ± Std | Min / Max | Mean Game Latency | Mean Nodes Evaluated | Win Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Shannon Entropy** | **4.27 ± 0.70** | 3 / 5 | 243.1 ms | 702 | 100% |
| **Knuth Minimax** | **4.53 ± 0.64** | 3 / 5 | 249.8 ms | 802 | 100% |
| **Irving Expected Size** | **4.53 ± 0.52** | 4 / 5 | 254.1 ms | 802 | 100% |
| **Most Parts (Kooi)** | **4.60 ± 0.63** | 4 / 6 | 258.4 ms | 762 | 100% |
| **Adaptive Strategy Selector** | **4.27 ± 0.70** | 3 / 5 | 701.0 ms | 623 | 100% |

### 5.2 Exact Optimality Gap Benchmark ($3\text{ pegs}, 3\text{ colors}$)
| Algorithm | Mean Guesses | Optimality Gap vs. DP Optimum | Theoretical Status |
| :--- | :---: | :---: | :--- |
| **Exact Tree Search (DP)** | **2.733** | **0.000 (Reference)** | Provably Optimal (Game-Tree Minimax DP) |
| **Shannon Entropy** | **2.867** | **+0.133 guesses** | Greedy 1-ply Approximation |
| **Knuth Minimax** | **2.867** | **+0.133 guesses** | Greedy 1-ply Approximation |

### 5.3 Board Complexity Scaling Analysis
| Configuration | Code Space Size | Mean Guesses | Mean Game Latency | Mean Turn Latency |
| :--- | :---: | :---: | :---: | :---: |
| **Small (3p/4c)** | $4^3 = 64$ | 3.20 ± 0.63 | 3.4 ms | 1.1 ms |
| **Standard (4p/6c)** | $6^4 = 1,296$ | 4.20 ± 0.79 | 254.2 ms | 60.5 ms |
| **Expanded (5p/6c)** | $6^5 = 7,776$ | 4.80 ± 0.42 | 988.2 ms | 205.9 ms |
| **Wide (4p/8c)** | $8^4 = 4,096$ | 4.90 ± 0.32 | 945.8 ms | 193.0 ms |
| **Distinct (5p/8c no repeats)** | $P(8,5) = 6,720$ | 5.40 ± 0.52 | 1266.7 ms | 234.6 ms |

### 5.4 Search Deadline & Budget Tradeoff ($4\text{ pegs}, 6\text{ colors}$)
| Turn Deadline | Mean Guesses | Mean Nodes Evaluated | Mean Game Latency | Empirical Finding |
| :--- | :---: | :---: | :---: | :--- |
| **10 ms** | 4.50 ± 0.71 | 276 | 61.6 ms | Rapid heuristic estimation under strict budget |
| **50 ms** | 4.40 ± 0.52 | 521 | 154.7 ms | Balanced tradeoff between latency and partition breadth |
| **200 ms** | 4.80 ± 0.92 | 715 | 412.8 ms | Extended candidate evaluation |
| **1000 ms (unconstrained)** | 4.80 ± 0.92 | 947 | 1197.1 ms | Exhaustive partition scoring |

---

## 6. Running the Test Suite

Execute the comprehensive unit and integration test suite:

```bash
pytest -v
```

All 109 tests cover:
- Game engine rules, repeated colors, and feedback calculation.
- Secret encapsulation boundaries and turn progressions.
- Exact game-tree DP search and optimality verification.
- Shannon entropy, Knuth minimax, Irving expected size, and partition heuristics.
- Anytime search workers and interactive CLI command parsers.
- Experiment runner, statistical aggregation, and CSV/JSONL export.

---

## 7. Project Documentation

- [`docs/algorithms.md`](docs/algorithms.md): In-depth theoretical foundations, mathematical formulations, and algorithmic trade-offs for all implemented search strategies.
- [`docs/dynamic_tui_architecture.md`](docs/dynamic_tui_architecture.md): Technical breakdown of the Rich TUI, asynchronous worker threading, and live inspection subsystem.
- [`results/REPORT.md`](results/REPORT.md): Full empirical evaluation report with per-trial breakdown.

---

## 8. License

Developed for academic coursework. Released under the MIT License.
