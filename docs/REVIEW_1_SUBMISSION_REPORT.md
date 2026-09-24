# Vellore Institute of Technology
### (Deemed to be University under section 3 of UGC Act, 1956)
## BCSE307P – Compiler Design Lab
### Report Submission Guidelines

---

**Project Title:** OptiGuard – An Adaptive Compiler Optimization Framework with Degradation Detection and Safe Rollback  
**Code Repository:** https://github.com/rithika20252024/optiguard  

---

### Team Member(s): Max Three members

| S. No | Register No | Name | Contributions |
| :---: | :---: | :---: | :--- |
| 1 | 24BCT0156 | Aesha Singh | Common Subexpression Elimination (value numbering) and strength reduction; IR feature extractor; cost function J(IR) and $\Delta$J degradation detection; adaptive pass scheduler; literature survey (papers 1–8) and novelty section |
| 2 | 24BCE2984 | Rithika | Lexer, recursive-descent parser, TAC/CFG generation; Constant Folding, Algebraic Simplification, Dead-Code Elimination; stack-based snapshot, rollback engine and tabu list; benchmark evaluation; literature survey (papers 9–15) and problem statement |

---

## Problem Identification & Objectives – 2M

### Problem Statement
Production compilers such as GCC and LLVM/Clang run a fixed, preset order of optimization passes inside levels like -O1, -O2 and -O3. Compiler transformations are non-commutative, so no single ordering suits every program, and with N passes there are N! possible orderings. Each pass is designed assuming a local benefit, yet in practice an apparently beneficial pass can degrade the IR and yield worse machine code. Three typical causes are register-pressure explosion (aggressive CSE or LICM extends live ranges and forces memory spills), code bloat and instruction-cache thrashing (aggressive inlining and unrolling), and phase destabilization (an early pass destroys the canonical patterns that later passes need).

The gap is that passes run speculatively and irreversibly. Existing compilers and autotuners search for good orderings offline or at flag level, but none measure the IR between passes, and none can atomically undo a harmful pass. This project addresses the need for a compiler that treats every optimization pass as a transaction: measure it, keep it if it helps, and roll it back if it hurts.

### Objectives (Minimum 3)
* **Frontend and IR pipeline:** build a lexer and recursive-descent parser for a procedural C-subset that lowers programs to observable Three-Address Code (TAC) and a Control Flow Graph (CFG).
* **Optimization suite:** implement Constant Folding and Propagation, Algebraic Simplification and Strength Reduction, Dead-Code Elimination, and CSE via Value Numbering, each reporting the instructions it changes.
* **Multi-objective cost function:** define J(IR) = w1·N_instructions + w2·R_live_ranges + w3·C_alu_cycles and score every intermediate IR state.
* **Degradation detection:** compute $\Delta$J = J(IR_new) − J(IR_prev) after every pass, and raise a degradation interrupt when $\Delta$J $\ge$ 0 or a register-pressure threshold is breached.
* **Transactional rollback:** use stack-based snapshots to restore the IR exactly to the last checkpoint and record the offending pass on an IR-state tabu list.
* **Adaptive pass scheduler:** choose the next pass from real-time IR structural features instead of a hardcoded list, and evaluate it against a fixed-order baseline on a benchmark set.

Objectives are kept specific and measurable: instruction count, live-range count and ALU-cycle cost before versus after optimization, number of degradations detected and rolled back, and final J(IR) against the fixed-order baseline.

---

## Literature Survey – 2M

The table below summarizes 15 relevant papers, tools and existing systems.

| S.No | Title / Author / Year | Methodology | Findings | Gap Identified |
| :---: | :--- | :--- | :--- | :--- |
| 1 | Lattner & Adve, 2004. LLVM: A Compilation Framework for Lifelong Program Analysis & Transformation (CGO) | Typed SSA-based IR with a modular pass manager | Pass pipelines are composed from reusable passes over a common IR | Fixed -O levels; no per-pass measurement of degradation and no undo |
| 2 | Bodin, Kisuki, Knijnenburg, O'Boyle & Rohou, 1998. Iterative Compilation in a Non-Linear Optimisation Space | Repeatedly compiles and runs a program with different optimization parameters | Search over parameters beats static settings on the target | Needs many full compile-and-run cycles; slow and machine-specific |
| 3 | Cooper, Schielke & Subramanian, 1999. Optimizing for Reduced Code Space using Genetic Algorithms (LCTES) | Genetic algorithm evolves pass sequences for code size | Evolved sequences outperform the fixed default ordering | Offline search over hours; a bad sequence is only scored poorly, the culprit pass is never isolated |
| 4 | Kulkarni, Hines, Hiser, Whalley, Davidson & Jones, 2004. Fast Searches for Effective Optimization Phase Sequences (PLDI) | Search over phase sequences with pruning of redundant sequences | Cuts search cost while finding good sequences | Requires execution or simulation for feedback; no monitoring between passes |
| 5 | Pan & Eigenmann, 2006. Fast and Effective Orchestration of Compiler Optimizations for Automatic Performance Tuning (CGO) | Iterative elimination of harmful optimization flags using runtime profiles | Selects flag combinations that improve measured performance | Needs runtime profiling on hardware; decisions are at flag level, not IR level |
| 6 | Agakov et al., 2006. Using Machine Learning to Focus Iterative Optimization (CGO) | Learns from past programs to focus the search on promising transformations | Reduces the number of search iterations needed | Model quality depends on training data; no safety net if a prediction is wrong |
| 7 | Fursin et al., 2011. Milepost GCC: Machine Learning Enabled Self-Tuning Compiler (IJPP) | 56 static program features feed supervised learning that predicts optimization flags | Automatically tunes GCC for unseen programs | Macro-flag granularity; black-box prediction with no internal revert |
| 8 | Ansel et al., 2014. OpenTuner: An Extensible Framework for Program Autotuning (PACT) | Ensemble of search techniques for autotuning arbitrary parameters | General framework reusable across domains | Domain-agnostic and measurement-driven; knows nothing about IR state |
| 9 | Ashouri et al., 2017. MiCOMP: Mitigating the Compiler Phase-Ordering Problem Using Optimization Sub-Sequences and Machine Learning (ACM TACO) | Clusters optimization sub-sequences and predicts the best with ML | Improves over standard -O levels on benchmark suites | Predicts sequences ahead of time; no in-flight detection of a harmful pass |
| 10 | Ashouri, Killian, Cavazos, Palermo & Silvano, 2018. A Survey on Compiler Autotuning Using Machine Learning (ACM CSUR) | Survey of two decades of ML-based compiler autotuning | Classifies selection and phase-ordering approaches | Highlights degradation and robustness as open problems and calls for self-stabilizing compilers |
| 11 | Haj-Ali et al., 2020. AutoPhase: Juggling HLS Phase Orderings in Random Forests with Deep Reinforcement Learning (MLSys) | Deep RL over LLVM pass ordering using IR features | Learns orderings that improve HLS cycle counts | Needs an expensive evaluation per step and heavy training; no rollback of bad steps |
| 12 | Whitfield & Soffa, 1997. An Approach for Exploring Code Improving Transformations (TOPLAS) | Formal model of enabling and disabling interactions between transformations | Shows that one transformation can create or destroy opportunities for another | Analyses interactions but offers no runtime mechanism to recover from a harmful one |
| 13 | Briggs, Cooper & Torczon, 1994. Improvements to Graph Coloring Register Allocation (TOPLAS) | Graph-coloring allocator with optimistic coloring and spilling | Better allocation and fewer spills in practice | Spills appear only at the end; earlier passes that inflate register pressure are not flagged |
| 14 | Lopes, Lee, Hur, Liu & Regehr, 2021. Alive2: Bounded Translation Validation for LLVM (PLDI) | Checks that an optimized function refines the original | Finds real miscompilations in LLVM passes | Validates correctness only; says nothing about whether a pass made code worse |
| 15 | Glover, 1989. Tabu Search, Part I (ORSA Journal on Computing) | Metaheuristic that forbids recently visited moves through a tabu list | Avoids cycling and escapes local optima | Not applied to per-IR-state pass rejection in compilers, which is what OptiGuard adds |

### Research gaps and project motivation
The surveyed work falls into three groups. Search-based approaches (iterative compilation, genetic algorithms, OpenTuner) and learning-based approaches (Milepost, MiCOMP, AutoPhase) look for a good pass ordering or flag set, but they work offline or at macro-flag level and depend on expensive measurement on target hardware. Formal work on transformation interactions and on translation validation shows that passes can undermine each other and can even be wrong, yet it offers no way to recover at compile time, and the register-allocation literature only reveals spills after the fact. Autotuning surveys explicitly name optimization degradation as an unsolved problem and ask for self-stabilizing compilers. None of these systems measures the IR between passes or reverts a single harmful pass. This motivates OptiGuard, which scores each IR state in situ and treats every pass as a commit-or-rollback transaction.

---

## Novelty – 2 M

OptiGuard differs from the literature reviewed in the following ways:
* **Transactional compilation model:** database-style atomicity and consistency are applied to phase ordering, so every pass is a speculative transaction that is either committed or rolled back. Existing pipelines are sequential and irreversible.
* **In-situ cost evaluation J(IR):** passes are scored directly on the TAC using instruction count, live intervals and operator-weighted ALU cycles, which removes the target-hardware re-execution that GA and iterative-compilation approaches need.
* **Micro-pass granularity with atomic rollback:** degradation is detected and reverted at the level of a single pass, so the culprit is isolated. Prior work discards or merely penalizes an entire sequence.
* **Tabu-driven adaptive scheduling:** a degrading pass is recorded in a tabu list for that IR state, which prevents cyclic rollbacks and steers the scheduler toward alternative passes chosen from IR features.

*Formal novelty statement:* unlike existing compiler optimization pipelines that apply transformations sequentially and irreversibly regardless of intermediate code deterioration, OptiGuard introduces a fail-safe, transactional compiler architecture that combines IR feature profiling with a multi-objective cost evaluation model and a stack-based state rollback engine. Passes are accepted only when they yield a quantifiable structural improvement.

---

## Project Timeline & Assessment Schedule

| S.No | Assessment Details | Scope & Deliverables | Evaluation Weightage | Due Date |
| :---: | :--- | :--- | :---: | :---: |
| **1** | **Assessment 8**<br>Project Review 1 | • Problem Identification & Objectives (2M)<br>• Literature Survey (2M)<br>• Novelty (2M)<br>• Presentation & Q&A (2M) | 10 Marks | **24.09.2026** (EOD) /<br>24th–25th Sep 2026 |
| **2** | **25% Implementation Review** | Working prototype demo: Lexer, Parser, AST, Three-Address Code (TAC), 3 Optimization Passes (Constant Folding, Algebraic Simplification, DCE), and Metrics Evaluator | 2 Marks | **08/10/2026**<br>(1st week of October) |
| **3** | **Assessment 9**<br>Project Review 2 | • 75% Implementation progress: IR Feature Profiler, Degradation Detection Unit, Stack Rollback (6M)<br>• Progress Report / Documentation (2M)<br>• Presentation & Q&A (2M) | 10 Marks | **3rd Week of October 2026** |
| **4** | **Assessment 10**<br>Project Demo & Outcome | • 100% Project Completion & Final Demo (3M)<br>• Individual Contribution (3M)<br>• Final Research Manuscript / Patent Specification (4M) | 10 Marks | **4th Week of October 2026** |
