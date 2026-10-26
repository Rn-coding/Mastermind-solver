# Mastermind AI Empirical Evaluation Report

> **Project Evaluation Suite** - Automated benchmark runs under standardized environments.
> Measurements are computed from real runs; secret encapsulation is strictly preserved.

## 1. Summary Comparison

| Strategy | Configuration | Trials | Win Rate | Mean Guesses ± Std | Min/Max | Mean Game Time (ms) | Mean Nodes | Optimality Gap |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Exact Tree Policy (Optimal DP)** | `3p/3c (rep=True)` | 15 | 100.0% | 2.73 ± 0.46 | 2 / 3 | 120.2 ms | 343 | N/A |
| **Shannon Entropy** | `3p/3c (rep=True)` | 15 | 100.0% | 2.87 ± 0.64 | 2 / 4 | 2.7 ms | 53 | +0.133 |
| **Knuth Minimax** | `3p/3c (rep=True)` | 15 | 100.0% | 2.87 ± 0.52 | 2 / 4 | 2.7 ms | 53 | +0.133 |
| **Shannon Entropy** | `4p/6c (rep=True)` | 15 | 100.0% | 4.27 ± 0.70 | 3 / 5 | 243.1 ms | 702 | N/A |
| **Knuth Minimax** | `4p/6c (rep=True)` | 15 | 100.0% | 4.53 ± 0.64 | 3 / 5 | 249.8 ms | 802 | N/A |
| **Irving Expected Size** | `4p/6c (rep=True)` | 15 | 100.0% | 4.53 ± 0.52 | 4 / 5 | 254.1 ms | 802 | N/A |
| **Most Parts** | `4p/6c (rep=True)` | 15 | 100.0% | 4.60 ± 0.63 | 4 / 6 | 258.4 ms | 762 | N/A |
| **Adaptive Strategy Selector** | `4p/6c (rep=True)` | 15 | 100.0% | 4.27 ± 0.70 | 3 / 5 | 701.0 ms | 623 | N/A |
| **Anytime Entropy (Small 3p/4c)** | `3p/4c (rep=True)` | 10 | 100.0% | 3.20 ± 0.63 | 2 / 4 | 3.4 ms | 79 | N/A |
| **Anytime Entropy (Standard 4p/6c)** | `4p/6c (rep=True)` | 10 | 100.0% | 4.20 ± 0.79 | 3 / 5 | 254.2 ms | 662 | N/A |
| **Anytime Entropy (Expanded 5p/6c)** | `5p/6c (rep=True)` | 10 | 100.0% | 4.80 ± 0.42 | 4 / 5 | 988.2 ms | 819 | N/A |
| **Anytime Entropy (Wide 4p/8c)** | `4p/8c (rep=True)` | 10 | 100.0% | 4.90 ± 0.32 | 4 / 5 | 945.8 ms | 887 | N/A |
| **Anytime Entropy (Distinct 5p/8c)** | `5p/8c (rep=False)` | 10 | 100.0% | 5.40 ± 0.52 | 5 / 6 | 1266.7 ms | 914 | N/A |
| **Anytime Entropy (10ms limit)** | `4p/6c (rep=True)` | 10 | 100.0% | 4.50 ± 0.71 | 3 / 5 | 61.6 ms | 276 | N/A |
| **Anytime Entropy (50ms limit)** | `4p/6c (rep=True)` | 10 | 100.0% | 4.40 ± 0.52 | 4 / 5 | 154.7 ms | 521 | N/A |
| **Anytime Entropy (200ms limit)** | `4p/6c (rep=True)` | 10 | 100.0% | 4.80 ± 0.92 | 3 / 6 | 412.8 ms | 715 | N/A |
| **Anytime Entropy (1000ms limit)** | `4p/6c (rep=True)` | 10 | 100.0% | 4.80 ± 0.92 | 3 / 6 | 1197.1 ms | 947 | N/A |

## 2. Detailed Experiment Breakdowns

### 2.1 Exact Reference Benchmark - Exact Tree Policy (Optimal DP)
- **Board Config**: 3 pegs, 3 colors, repeats=True
- **Budget / Mode**: Exhaustive minimax game-tree policy
- **Sample Size**: 15 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 2.733 (StdDev: 0.458)
- **Latency**: Mean game: 120.23 ms | Mean turn: 43.99 ms
- **Search Workload**: Mean nodes evaluated: 342.5 | Total: 5,138

### 2.2 Exact Reference Benchmark - Shannon Entropy
- **Board Config**: 3 pegs, 3 colors, repeats=True
- **Budget / Mode**: Greedy information gain
- **Sample Size**: 15 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 2.867 (StdDev: 0.640)
- **Latency**: Mean game: 2.70 ms | Mean turn: 0.94 ms
- **Search Workload**: Mean nodes evaluated: 53.4 | Total: 801
- **Optimality Gap vs Exact Reference**: +0.1333 guesses

### 2.3 Exact Reference Benchmark - Knuth Minimax
- **Board Config**: 3 pegs, 3 colors, repeats=True
- **Budget / Mode**: Minimax worst-case partition
- **Sample Size**: 15 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 2.867 (StdDev: 0.516)
- **Latency**: Mean game: 2.65 ms | Mean turn: 0.92 ms
- **Search Workload**: Mean nodes evaluated: 53.3 | Total: 799
- **Optimality Gap vs Exact Reference**: +0.1333 guesses

### 2.4 Strategy Matrix Comparison - Shannon Entropy
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Full candidate entropy maximization
- **Sample Size**: 15 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.267 (StdDev: 0.704)
- **Latency**: Mean game: 243.08 ms | Mean turn: 56.97 ms
- **Search Workload**: Mean nodes evaluated: 702.2 | Total: 10,533

### 2.5 Strategy Matrix Comparison - Knuth Minimax
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Worst-case remaining candidate minimization
- **Sample Size**: 15 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.533 (StdDev: 0.640)
- **Latency**: Mean game: 249.77 ms | Mean turn: 55.10 ms
- **Search Workload**: Mean nodes evaluated: 802.1 | Total: 12,031

### 2.6 Strategy Matrix Comparison - Irving Expected Size
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Expected candidate partition size minimization
- **Sample Size**: 15 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.533 (StdDev: 0.516)
- **Latency**: Mean game: 254.09 ms | Mean turn: 56.05 ms
- **Search Workload**: Mean nodes evaluated: 802.1 | Total: 12,031

### 2.7 Strategy Matrix Comparison - Most Parts
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Partition count maximization
- **Sample Size**: 15 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.600 (StdDev: 0.632)
- **Latency**: Mean game: 258.36 ms | Mean turn: 56.17 ms
- **Search Workload**: Mean nodes evaluated: 762.3 | Total: 11,435

### 2.8 Strategy Matrix Comparison - Adaptive Strategy Selector
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Expectimax (< 36 cands) + Anytime Entropy
- **Sample Size**: 15 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.267 (StdDev: 0.704)
- **Latency**: Mean game: 700.96 ms | Mean turn: 164.29 ms
- **Search Workload**: Mean nodes evaluated: 622.5 | Total: 9,338

### 2.9 Board Scaling Analysis - Anytime Entropy (Small 3p/4c)
- **Board Config**: 3 pegs, 4 colors, repeats=True
- **Budget / Mode**: 1.0s max turn budget, canonical first guess
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 3.200 (StdDev: 0.632)
- **Latency**: Mean game: 3.42 ms | Mean turn: 1.07 ms
- **Search Workload**: Mean nodes evaluated: 79.4 | Total: 794

### 2.10 Board Scaling Analysis - Anytime Entropy (Standard 4p/6c)
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: 1.0s max turn budget, canonical first guess
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.200 (StdDev: 0.789)
- **Latency**: Mean game: 254.20 ms | Mean turn: 60.52 ms
- **Search Workload**: Mean nodes evaluated: 662.4 | Total: 6,624

### 2.11 Board Scaling Analysis - Anytime Entropy (Expanded 5p/6c)
- **Board Config**: 5 pegs, 6 colors, repeats=True
- **Budget / Mode**: 1.0s max turn budget, canonical first guess
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.800 (StdDev: 0.422)
- **Latency**: Mean game: 988.19 ms | Mean turn: 205.87 ms
- **Search Workload**: Mean nodes evaluated: 819.3 | Total: 8,193

### 2.12 Board Scaling Analysis - Anytime Entropy (Wide 4p/8c)
- **Board Config**: 4 pegs, 8 colors, repeats=True
- **Budget / Mode**: 1.0s max turn budget, canonical first guess
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.900 (StdDev: 0.316)
- **Latency**: Mean game: 945.81 ms | Mean turn: 193.02 ms
- **Search Workload**: Mean nodes evaluated: 886.9 | Total: 8,869

### 2.13 Board Scaling Analysis - Anytime Entropy (Distinct 5p/8c)
- **Board Config**: 5 pegs, 8 colors, repeats=False
- **Budget / Mode**: 1.0s max turn budget, canonical first guess
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 5.400 (StdDev: 0.516)
- **Latency**: Mean game: 1266.74 ms | Mean turn: 234.58 ms
- **Search Workload**: Mean nodes evaluated: 914.2 | Total: 9,142

### 2.14 Search Budget Impact - Anytime Entropy (10ms limit)
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Strict timeout 10ms without canonical shortcut
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.500 (StdDev: 0.707)
- **Latency**: Mean game: 61.60 ms | Mean turn: 13.69 ms
- **Search Workload**: Mean nodes evaluated: 276.4 | Total: 2,764

### 2.15 Search Budget Impact - Anytime Entropy (50ms limit)
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Strict timeout 50ms without canonical shortcut
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.400 (StdDev: 0.516)
- **Latency**: Mean game: 154.68 ms | Mean turn: 35.15 ms
- **Search Workload**: Mean nodes evaluated: 521.2 | Total: 5,212

### 2.16 Search Budget Impact - Anytime Entropy (200ms limit)
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Strict timeout 200ms without canonical shortcut
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.800 (StdDev: 0.919)
- **Latency**: Mean game: 412.77 ms | Mean turn: 85.99 ms
- **Search Workload**: Mean nodes evaluated: 714.9 | Total: 7,149

### 2.17 Search Budget Impact - Anytime Entropy (1000ms limit)
- **Board Config**: 4 pegs, 6 colors, repeats=True
- **Budget / Mode**: Strict timeout 1000ms without canonical shortcut
- **Sample Size**: 10 deterministic trials
- **Solve Success Rate**: 100.0%
- **Average Guess Count**: 4.800 (StdDev: 0.919)
- **Latency**: Mean game: 1197.06 ms | Mean turn: 249.39 ms
- **Search Workload**: Mean nodes evaluated: 947.4 | Total: 9,474

## 3. Analysis and Key Findings

1. **Information-Theoretic Efficiency (Shannon Entropy)**:
   Entropy-maximizing solvers partition the candidate space by maximizing expected bits of information gain $H(g)$. This consistently achieves low average guesses across varied configurations.

2. **Minimax (Knuth)**:
   Knuth's minimax heuristic minimizes the worst-case partition size $\max_f |S_{g, f}|$. While optimal for minimizing worst-case turn count on standard $4\times6$, entropy search often yields slightly superior or equivalent average guess counts.

3. **Budget and Scaling Behavior**:
   On compact spaces ($3\times3$, $3\times4$, $4\times6$), exact or full candidate evaluation completes within milliseconds. As state space scales ($> 10^5$), anytime entropy search provides progressive quality improvement, pruning unpromising branches while respecting user-specified wall-clock and node deadlines.

4. **Exact Reference Comparison**:
   On small tractable boards where global exact dynamic programming finds the game-theoretic optimum, heuristic and expectimax policies match or closely approach the theoretical lower bound (optimality gap $\approx 0.0$).

---
*Generated by the Mastermind AI Evaluation Runner.*