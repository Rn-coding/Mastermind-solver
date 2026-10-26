# Mastermind AI: Algorithmic Foundations & Strategy Analysis

This internal document details the mathematical formulations, algorithmic implementations, and architectural decisions behind the Mastermind AI solvers developed for this project.

---

## 1. Mathematical Formulation & State-Space Representation

Mastermind is a partially observable, sequential deduction game:
- **Code Space ($G$)**: The set of all legal codes of length $N$ (`num_pegs`) drawn from an alphabet of size $K$ (`num_colors`). With replacement, $|G| = K^N$.
- **Hidden Secret ($s^* \in G$)**: Fixed prior to play and concealed from the solver.
- **Turn Feedback ($\mathcal{F}$)**: A pair $(b, w)$ where:
  - $b$ (exact matches): correct color in the correct position.
  - $w$ (misplaced matches): correct color in an incorrect position, calculated without double-counting exact matches.
- **Belief State ($C_t \subseteq G$)**: The set of candidate secrets consistent with the entire observation history up to turn $t$:
  $$C_t = \{ c \in G \mid \forall (g_i, f_i) \in \text{History}_{1..t}, \text{Feedback}(c, g_i) = f_i \}$$
  Under a uniform prior, the posterior probability of candidate $c$ being the true secret is $P(c \mid \text{History}_t) = \frac{1}{|C_t|}$.

### Feedback Partitioning
For any candidate guess $g \in G$, $g$ induces a partition of the current belief state $C$ into disjoint subsets:
$$C = \bigcup_{fb \in \mathcal{F}} C_{fb}(g), \quad \text{where } C_{fb}(g) = \{ c \in C \mid \text{Feedback}(c, g) = fb \}$$
The probability of observing feedback $fb$ upon playing guess $g$ is:
$$P(fb \mid g) = \frac{|C_{fb}(g)|}{|C|}$$

---

## 2. Implemented Heuristic Solvers

### 2.1 Knuth's Minimax Algorithm (1977)
Donald Knuth proved that standard Mastermind ($4$ pegs, $6$ colors, $1,296$ codes) can always be solved in at most **$5$ turns**.

- **Objective**: Minimize the worst-case size of the candidate set remaining on the next turn.
  $$\text{Score}_{\text{Knuth}}(g) = \max_{fb \in \mathcal{F}} |C_{fb}(g)|$$
  $$\hat{g} = \arg\min_{g \in G} \text{Score}_{\text{Knuth}}(g)$$
- **Tie-Breaking Rule**: If multiple guesses achieve the minimum worst-case partition size, Knuth's rule strictly prefers a guess that is an active candidate ($g \in C$). If $g \in C$, there is a $\frac{1}{|C|}$ probability of immediate victory on the current turn.

### 2.2 Shannon Entropy / Information Gain Heuristic (Bestavros 1986, Neuwirth 1982)
While Knuth optimizes worst-case depth, Claude Shannon's information theory optimizes expected information gain (entropy reduction), achieving a lower **average** number of turns (~$4.34$ guesses).

- **Objective**: Maximize the Shannon entropy of the feedback distribution in bits:
  $$H(g) = - \sum_{fb \in \mathcal{F}} P(fb \mid g) \log_2 P(fb \mid g) = \log_2(|C|) - \frac{1}{|C|} \sum_{fb \in \mathcal{F}} |C_{fb}(g)| \log_2(|C_{fb}(g)|)$$
- **Intuition**: A guess that partitions candidates into many equally sized subsets yields high entropy, maximizing the expected reduction in uncertainty regardless of which feedback the environment returns.

### 2.3 Irving's Expected Size Heuristic (1978)
Robert Irving proposed directly minimizing the expected candidate count remaining after the turn.

- **Objective**:
  $$\mathbb{E}[|C'| \mid g] = \sum_{fb \in \mathcal{F}} P(fb \mid g) \cdot |C_{fb}(g)| = \frac{1}{|C|} \sum_{fb \in \mathcal{F}} |C_{fb}(g)|^2$$
- **Comparison to Entropy**: Minimizing $\sum |C_{fb}|^2$ is closely related to maximizing entropy (since $\log x \approx x - 1$), but penalizes large outlier partitions quadratically.

### 2.4 Kooi's Most Parts Heuristic (2005)
- **Objective**: Maximize the count of non-empty feedback categories:
  $$\text{Score}_{\text{Kooi}}(g) = |\{ fb \in \mathcal{F} \mid |C_{fb}(g)| > 0 \}|$$
- **Property**: Highly efficient computationally because it avoids logarithmic or quadratic floating-point arithmetic while encouraging wide dispersion of candidates.

---

## 3. Multi-Ply Search & Exact Policy Trees

### 3.1 Exact Policy Tree Search (`ExactPolicySolver`)
Local 1-ply heuristics (Knuth, Entropy) evaluate only the immediate next turn. They are greedy approximations of the true game tree.

- **Dynamic Programming with Memoization**:
  For small configurations ($|G| \le 100$ or $|C| \le 81$), our `ExactPolicySolver` constructs the optimal decision tree:
  - **Expected Total Guesses**:
    $$\text{Cost}(C) = 1 + \min_{g \in G} \sum_{fb \neq \text{solved}} \frac{|C_{fb}|}{|C|} \text{Cost}(C_{fb})$$
  - **Worst-Case Guesses**:
    $$\text{Cost}(C) = 1 + \min_{g \in G} \max_{fb \neq \text{solved}} \text{Cost}(C_{fb})$$
- **Transposition Table**: Memoized on the canonical `frozenset(candidates)`, preventing recomputation of identical sub-belief states reached via different guess paths.

### 3.2 Bounded Expectimax (`BoundedExpectimaxSolver`)
When full tree search is intractable but lookahead beyond 1 ply is desirable:
- Expands the game tree to a configurable depth limit $d$ (e.g. $d=2$ or $d=3$).
- Alternates between decision nodes (AI minimizing expected cost) and chance nodes (feedback probability $P(fb) = \frac{|C_{fb}|}{|C|}$).
- **Frontier Evaluation**: At depth limit $d$, remaining turns are estimated from belief entropy:
  $$\text{FrontierCost}(C) \approx 1.0 + \frac{\log_2(|C|)}{2.0}$$

---

## 4. Scaling Across Board Sizes

The primary computational bottleneck in Mastermind is partition evaluation: evaluating $|G|$ candidate guesses against $|C|$ remaining candidates requires $\mathcal{O}(|G| \cdot |C|)$ feedback computations per turn.

| Board Configuration | Code Space $|G|$ | Typical Turn-1 Workload | Recommended Strategy |
| :--- | :--- | :--- | :--- |
| **Small** (e.g. 2 pegs, 3 colors) | $3^2 = 9$ | $9 \times 9 = 81$ | **Exact Policy Tree Search** (Provably optimal, $< 1$ ms) |
| **Quick** (3 pegs, 4 colors) | $4^3 = 64$ | $64 \times 64 = 4,096$ | **2-Ply Bounded Expectimax** ($< 50$ ms) |
| **Standard** (4 pegs, 6 colors) | $6^4 = 1,296$ | $1,296 \times 1,296 \approx 1.68 \times 10^6$ | **1-Ply Entropy Heuristic** with Turn-1 Symmetry Reduction ($~100$ ms) |
| **Master** (5 pegs, 8 colors) | $8^5 = 32,768$ | $32,768^2 \approx 1.07 \times 10^9$ | **Hybrid Sampled Heuristic** ($150$ sampled guesses, $< 200$ ms) |
| **Grandmaster** (6 pegs, 10 colors)| $10^6 = 1,000,000$ | $10^{12}$ | **Lazy Constraint Satisfaction (CSP)** with Genetic/Local Candidate Sampling |

### Strategy Selection Algorithm (`StrategySelector`)
Rather than relying on arbitrary hardcoded board-size switches, the solver profiles the **instantaneous workload** of the current belief state:
1. **Workload Estimator**: Evaluates $\mathcal{W} = |C_t| \times \min(|G|, \text{budget.max\_guesses})$.
2. **Turn-1 Symmetry Optimization**: On the initial turn, all color permutations are isomorphic. Playing canonical guesses (e.g., `(0, 0, 1, 1)`) collapses the initial search space from $1,296$ to just a handful of equivalence classes.
3. **Adaptive Thresholds**:
   - $\mathcal{W} \le 15,000 \implies$ Exact Tree Search.
   - $15,000 < \mathcal{W} \le 60,000 \implies$ Bounded Expectimax.
   - $60,000 < \mathcal{W} \le 1,500,000 \implies$ 1-Ply Shannon Entropy Heuristic.
   - $\mathcal{W} > 1,500,000 \implies$ Hybrid Sampled Constraint Heuristic.
4. **Graceful Fallback**: If time or node budgets are exhausted mid-search, the best evaluated guess is returned, falling back safely to any consistent candidate in $C_t$.
