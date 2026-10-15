# OptiGuard: Adaptive Compiler Optimization Framework with Degradation Detection and Safe Rollback

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/Tests-39%2F39%20Passed-brightgreen.svg)]()
[![Milestone](https://img.shields.io/badge/Milestone-100%25%20Complete-success.svg)]()

> **OptiGuard** is an IR-level compiler optimization framework that solves the **Phase-Ordering Problem** and prevents **Optimization Degradation**. Rather than executing a rigid, unverified sequence of passes, OptiGuard evaluates transformations using a multi-objective cost function $J(IR)$ and provides **transactional rollback** to guarantee monotonically non-degrading code generation.

---

## Key Highlights

- **Adaptive Phase Ordering:** Selects the next optimization pass at runtime using a 12-dimensional IR feature vector — no fixed pass sequence.
- **Degradation Detection:** Computes $J(IR) = w_1 \cdot \text{instrs} + w_2 \cdot \text{cycles} + w_3 \cdot \text{temps}$; flags any pass that doesn't strictly improve J.
- **Transactional Rollback:** Snapshots IR before each pass; if $\Delta J \geq 0$, atomically reverts to the prior stable state.
- **Tabu Search Convergence:** Tracks failed passes in a tabu list; terminates when all passes are exhausted.
- **6 Optimization Passes:** Constant Folding, Algebraic Simplification, Dead Code Elimination, CSE, Strength Reduction, Copy Propagation.
- **Zero Dependencies:** Pure Python 3.8+ — no external libraries.

---

## System Architecture

```
                  ┌──────────────────────────────┐
                  │    Source Code (C-Subset)    │
                  └──────────────┬───────────────┘
                                 │ Lexer & Parser
                                 ▼
                  ┌──────────────────────────────┐
                  │  Three-Address Code (TAC/IR) │
                  └──────────────┬───────────────┘
                                 │
                   ┌─────────────▼───────────────┐
             ┌────►│  IR Feature Profiler (12-d) │◄─────────────┐
             │     └─────────────┬───────────────┘              │
             │                   │ FeatureVector                │
             │     ┌─────────────▼───────────────┐              │
             │     │ Adaptive Pass Selector      │              │
             │     │ (Tabu Search Heuristic)     │              │
             │     └─────────────┬───────────────┘              │
             │                   │ Select Pass Pₖ               │
             │     ┌─────────────▼───────────────┐              │
             │     │  SnapshotStack.push(IR)     │              │
             │     └─────────────┬───────────────┘              │
             │                   │ Apply Optimization Pass      │
             │     ┌─────────────▼───────────────┐              │
             │     │    Transformed Candidate    │              │
             │     └─────────────┬───────────────┘              │
             │                   │ Compute J(IR_new)            │
             │     ┌─────────────▼───────────────┐              │
             │     │  Degradation Detector Unit  │              │
             │     └───────┬──────────────┬──────┘              │
      ΔJ < 0 (ACCEPT)      │              │  ΔJ ≥ 0 (ROLLBACK) │
             │             ▼              ▼                     │
             │     [commit() + accept]  [pop() + tabu] ─────────┘
             │             │
             └─────────────┤
                           ▼
                   ┌──────────────────────────────┐
                   │ Convergence / Budget Check   │
                   └──────────────┬───────────────┘
                                  │ All passes in tabu → Done
                                  ▼
                   ┌──────────────────────────────┐
                   │     Optimized TAC Output     │
                   └──────────────────────────────┘
```

---

## Project Status — 100% Complete ✅

| Component | Status | Description |
|---|---|---|
| Frontend (Lexer, Parser, AST) | ✅ Done | C-subset tokenization & recursive descent parsing |
| IR: TAC + clone/snapshot | ✅ Done | Three-address code with atomic deep-copy |
| Pass 1: Constant Folding | ✅ Done | Compile-time arithmetic + constant propagation |
| Pass 2: Algebraic Simplification | ✅ Done | x+0, x×1, x×0, x/1 identity elimination |
| Pass 3: Dead Code Elimination | ✅ Done | Backward liveness analysis, iterative fixed-point |
| Pass 4: CSE | ✅ Done | Available-expressions analysis |
| Pass 5: Strength Reduction | ✅ Done | x\*2→x+x, x\*4→t+t, power-of-two div |
| Pass 6: Copy Propagation | ✅ Done | Forward substitution + kill analysis |
| IR Feature Profiler | ✅ Done | 12-dimensional feature vector |
| Degradation Detector | ✅ Done | J(IR) cost function, ΔJ decision |
| Snapshot Stack | ✅ Done | LIFO transactional rollback |
| Adaptive Selector | ✅ Done | Heuristic scoring + tabu list |
| Adaptive Pipeline | ✅ Done | Full loop with budget, convergence |
| Benchmark Suite (8 programs) | ✅ Done | Automated runner + comparison table |
| CLI | ✅ Done | `python3 -m optiguard.cli` |
| 39 Unit Tests | ✅ Done | All 39 pass |
| Review 2 Report | ✅ Done | 75% implementation documentation |
| Final Report | ✅ Done | IEEE-style abstract, results, novelty |

---

## Quick Start

### 1. Run the Full Adaptive Demo
```bash
python3 demo.py
```

### 2. Run All Unit Tests
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### 3. Run Benchmark Suite
```bash
python3 benchmark/run_benchmarks.py
# Compare adaptive vs sequential:
python3 benchmark/run_benchmarks.py --compare
```

### 4. CLI Usage
```bash
# From file
python3 -m optiguard.cli input.c --verbose --features

# From stdin
echo "a = 10 * 2; b = a + 0; c = b;" | python3 -m optiguard.cli
```

### 5. Python API
```python
from optiguard.pipeline import OptiGuardPipeline

pipeline = OptiGuardPipeline(use_adaptive=True)
result = pipeline.optimize("""
    a = 10 * 2;
    b = a + 0;
    c = b;
""")
print(result.final_tac.dump())
print(result.improvement_summary)
```

---

## Sample Output

```
══════════════════  CASE 1: Canonical Phase-Ordering Benchmark  ══════════════════

[1] SOURCE CODE:
    a = 10 * 2;
    b = a + 0;
    c = b;

[2] INITIAL TAC / IR:
  0:  t0 = 10 * 2
  1:  a = t0
  2:  t1 = a + 0
  3:  b = t1
  4:  c = b
    → Instructions: 5 | Variables: 5 (Temps: 2) | Est. Cycles: 7

[3] IR FEATURE VECTOR:
    instructions=5  temp_density=0.40  const_density=0.33
    add_sub=0.20  mul=0.20  div=0.00  copy=0.60

[4] ADAPTIVE PASS EXECUTION:
    Pass                                   Decision       ΔJ       Instrs   Cycles
    ─────────────────────────────────────────────────────────────────────────────
    CopyPropagation                        ✗ ROLLBACK  +0.000     5→5      7→7
    DeadCodeElimination                    ✗ ROLLBACK  +0.000     5→5      7→7
    ConstantFolding                        ✓ COMMIT    -1.000     5→5      7→5
    ...

[6] QUANTITATIVE IMPROVEMENT REPORT:
    Instructions: 5 → 5  (−0 = 0.0% reduction)
    ALU Cycles  : 7 → 5  (−2 = 28.6% reduction)
```

---

## Project Structure

```
optiguard/
├── optiguard/
│   ├── frontend/          # Lexer, Parser, AST
│   ├── ir/                # TAC data structures
│   ├── passes/            # 6 optimization passes
│   ├── profiler/          # IR feature extraction
│   ├── rollback/          # Snapshot stack + degradation detector
│   ├── search/            # Adaptive pass selector (tabu search)
│   ├── metrics/           # Cost evaluator
│   ├── pipeline.py        # Main optimizer orchestrator
│   └── cli.py             # Command-line interface
├── benchmark/             # 8 benchmark programs + runner
├── docs/                  # All reports and presentations
├── tests/                 # 39 unit tests
├── demo.py                # Interactive demo
└── setup.py               # pip-installable
```

---

## Milestone Schedule

| Milestone | Target Date | Status | Deliverables |
|---|---|---|---|
| **Review 1** | Sep 24–25, 2026 | ✅ **Done** | Problem Formulation, Literature Survey, Novelty, Q&A |
| **25% Prototype** | 1st Wk Oct 2026 | ✅ **Done** | Lexer, Parser, AST, TAC IR, 3 Passes, Cost Evaluator |
| **Review 2 (75%)** | 3rd Wk Oct 2026 | ✅ **Done** | Profiler, Detector, Rollback, Adaptive Selector, 3 New Passes |
| **Final Demo (100%)** | 4th Wk Oct 2026 | ✅ **Done** | Full System, 8 Benchmarks, CLI, 39 Tests, Reports |

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
