# OptiGuard — Review 2 Progress Report (75% Implementation)

**Course:** Compiler Lab  
**Team:** OptiGuard Team  
**Date:** October 2026 (3rd Week)  
**Milestone:** 75% Implementation — Review 2 Submission

---

## 1. Overview

OptiGuard is an **adaptive compiler optimization framework** designed to solve the classical **Phase-Ordering Problem** in compiler design. The system applies optimization passes in an intelligent, data-driven sequence, detects when an optimization degrades the IR, and **atomically rolls back** to a prior safe state.

This report documents the progress from the 25% prototype (Lexer, Parser, TAC IR, 3 passes) to the 75% implementation milestone.

---

## 2. Completed Modules (75% Status)

### 2.1 New Optimization Passes (3 New Passes Added)

| Pass | Description | Technique |
|---|---|---|
| **Common Sub-expression Elimination (CSE)** | Detects duplicate `(op, arg1, arg2)` expressions and replaces recomputation with a copy | Available-Expressions Analysis (forward dataflow) |
| **Strength Reduction** | Replaces `x*2` → `x+x`, `x*4` → `t=x+x; t+t`, divides by powers-of-two with reciprocal multiply | Algebraic transformation |
| **Copy Propagation** | Substitutes `y = x` forward so later uses of `y` read `x` directly | Forward substitution with kill analysis |

**Total Passes: 6** (was 3 at 25%)

---

### 2.2 IR Feature Profiler (`optiguard/profiler/feature_profiler.py`)

Extracts a **12-dimensional FeatureVector** from any TACProgram:

```
FeatureVector:
  instruction_count     : Raw instruction count
  temp_density          : Fraction of instructions producing temporaries
  add_sub_fraction      : Fraction of binary ops that are +/-
  mul_fraction          : Fraction of binary ops that are *
  div_fraction          : Fraction of binary ops that are /
  copy_fraction         : Fraction of copy instructions
  constant_density      : Fraction of operands that are numeric constants
  distinct_variables    : Count of unique variable names
  register_pressure     : temp_count / distinct_variables
  has_binary_ops        : 1 if any binary op present
  has_copy_chains       : 1 if copy chains detected (a→b→c)
  has_repeated_expr     : 1 if duplicate (op,arg1,arg2) tuples found (CSE signal)
```

---

### 2.3 Transactional Snapshot Stack (`optiguard/rollback/snapshot_stack.py`)

A **LIFO stack** that stores deep-copy snapshots of the IR state before each pass application.

```python
stack.push(current_ir)        # Checkpoint
new_ir, modified = pass.run(current_ir)
if degraded:
    current_ir = stack.pop()  # ROLLBACK — O(1) operation
else:
    stack.commit()             # ACCEPT — discard snapshot
```

**Key properties:**
- Deep-copy isolation: mutations to `current_ir` after push do not affect snapshot
- O(1) push, pop, commit
- Empty-stack `pop()` raises `IndexError` (prevents silent data corruption)

---

### 2.4 Degradation Detector (`optiguard/rollback/degradation_detector.py`)

Implements the **multi-objective cost function** J(IR):

$$J(IR) = w_1 \cdot \text{instr\_count} + w_2 \cdot \text{cycle\_cost} + w_3 \cdot \text{temp\_count}$$

Default weights: $w_1 = 1.0$, $w_2 = 0.5$, $w_3 = 0.2$

**Decision Rule:**
- $\Delta J = J(IR_{new}) - J(IR_{prev})$
- If $\Delta J < 0$ → **ACCEPT** (strict improvement)
- If $\Delta J \geq 0$ → **ROLLBACK** (no improvement or degradation)

---

### 2.5 Adaptive Pass Selector with Tabu Search (`optiguard/search/adaptive_selector.py`)

Selects the next most-promising pass using **heuristic scoring** against the feature vector:

| Pass | Scoring Signal |
|---|---|
| ConstantFolding | `constant_density × 3 + has_binary_ops × 0.5` |
| AlgebraicSimplification | `add_sub_fraction × 2 + constant_density × 1.5` |
| DeadCodeElimination | `temp_density × 3 + copy_fraction × 1` |
| CSE | `has_repeated_expr × 5 + binary_mix × 0.5` |
| StrengthReduction | `mul_fraction × 3 + div_fraction × 4` |
| CopyPropagation | `copy_fraction × 2.5 + has_copy_chains × 3` |

**Tabu Mechanism:** When a pass fails the degradation check (ΔJ ≥ 0), it is added to the tabu list and excluded from future selection. Convergence is detected when all passes are in the tabu list.

---

### 2.6 Enhanced Adaptive Pipeline (`optiguard/pipeline.py`)

Full adaptive optimization loop with budget control:

```
WHILE budget_remaining AND NOT converged:
  features  ← FeatureProfiler.profile(current_IR)
  pass      ← AdaptiveSelector.select(features)  # tabu-aware
  IF pass IS None: BREAK  # convergence
  
  SnapshotStack.push(current_IR)
  (new_IR, modified) ← pass.run(current_IR)
  report ← DegradationDetector.check(J_prev, J_new)
  
  IF report.degraded OR NOT modified:
      current_IR ← SnapshotStack.pop()     # ROLLBACK
      AdaptiveSelector.add_to_tabu(pass)
  ELSE:
      SnapshotStack.commit()                # ACCEPT
      current_IR ← new_IR
      budget_remaining -= 1
```

---

### 2.7 Benchmark Suite (`benchmark/`)

8 benchmark programs covering:
- B1: Constant arithmetic chain
- B2: Dead code + multi-pass interaction
- B3: Symbolic identity elimination
- B4: Common sub-expression
- B5: Strength reduction targets
- B6: Copy propagation chain
- B7: Mixed optimization
- B8: Deep constant propagation

---

## 3. Test Results

```
Ran 39 tests in 0.013s

OK  ← ALL TESTS PASS
```

Test coverage:
- **Frontend:** 4 tests
- **IR:** 3 tests
- **Passes (6):** 11 tests
- **Rollback Engine:** 7 tests
- **Feature Profiler:** 4 tests
- **Adaptive Selector:** 3 tests
- **Pipeline (E2E):** 7 tests
- **Benchmark Suite:** 1 test (8 sub-tests)

---

## 4. Sample Optimization Results

| Program | Instr Before | Instr After | Cycle Before | Cycle After | Rollbacks |
|---|---|---|---|---|---|
| Constant Chain | 5 | 5 | 7 | 5 | 6 |
| Dead Code | 9 | — | — | — | — |
| Copy Chain | 4 | — | — | — | — |
| Deep Constants | 9 | — | — | — | — |

---

## 5. Architecture Diagram (Updated)

```
Source Code (C-Subset)
        │ Lexer + Parser
        ▼
  AST (Abstract Syntax Tree)
        │ IRGenerator
        ▼
  TAC (Three-Address Code)  ←─── SnapshotStack.pop() ─────────────┐
        │                                                          │
        │ FeatureProfiler                                          │
        ▼                                                          │
  FeatureVector (12-dim)                                           │
        │ AdaptivePassSelector (Tabu Search)                       │
        ▼                                                          │
  Selected Pass Pₖ                                                 │
        │ SnapshotStack.push(IR)                                   │
        ▼                                                          │
  Apply Pass → IR_new                                              │
        │ DegradationDetector: J(IR_new) vs J(IR_prev)             │
        ▼                                                          │
  ΔJ < 0 → ACCEPT (commit)     ΔJ ≥ 0 → ROLLBACK (restore) ───────┘
        │
        ▼
  Convergence / Budget Check
        │
        ▼
  Optimized TAC Output
```

---

## 6. Remaining Work (25% → Final Demo)

- [x] All 75% deliverables completed
- [ ] Full benchmark paper/report with tables
- [ ] IEEE-style abstract for Outcome requirement
- [ ] Individual contribution documentation
