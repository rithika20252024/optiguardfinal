#!/usr/bin/env python3
"""OptiGuard — Full Adaptive Demo with Rollback Visualization.

Demonstrates the complete 100% OptiGuard system:
  1. Frontend: Lexer → Parser → AST → TAC generation
  2. IR Feature Profiling
  3. Adaptive Pass Selection (Tabu Search)
  4. Transactional Snapshot + Rollback
  5. Degradation Detection (J(IR) cost function)
  6. Quantitative Benchmark Results

Run:
    python3 demo.py
"""

import sys
from optiguard.pipeline import OptiGuardPipeline
from optiguard.profiler.feature_profiler import FeatureProfiler


def sep(title="", ch="═", width=72):
    if title:
        pad = max(0, width - len(title) - 4)
        left = pad // 2
        right = pad - left
        print(f"\n{ch * left}  {title}  {ch * right}")
    else:
        print(ch * width)


def print_header():
    print(r"""
╔══════════════════════════════════════════════════════════════════════╗
║   ___       _   _  ____                     _                       ║
║  / _ \ _ __| |_(_)/ ___|_   _  __ _ _ __ __| |                      ║
║ | | | | '_ \| __| | |  _| | | |/ _` | '__/ _` |                     ║
║ | |_| | |_) | |_| | |_| | |_| | (_| | | | (_| |                     ║
║  \___/| .__/ \__|_|\____|\__,_|\__,_|_|  \__,_|                     ║
║       |_|   Adaptive Compiler Pass Optimizer — v1.0 (100% Demo)     ║
╚══════════════════════════════════════════════════════════════════════╝
""")


def run_adaptive_case(pipeline, case_num, title, source):
    sep(f"CASE {case_num}: {title}")

    print("\n[1] SOURCE CODE:")
    for line in source.strip().splitlines():
        print(f"    {line}")

    result = pipeline.optimize(source)

    print("\n[2] INITIAL TAC / IR:")
    print(result.initial_tac.dump())
    print(f"    → {result.initial_metrics}")

    print("\n[3] IR FEATURE VECTOR:")
    fv = FeatureProfiler.profile(result.initial_tac)
    print(f"    instructions={fv.instruction_count}  "
          f"temp_density={fv.temp_density:.2f}  "
          f"const_density={fv.constant_density:.2f}")
    print(f"    add_sub={fv.add_sub_fraction:.2f}  "
          f"mul={fv.mul_fraction:.2f}  "
          f"div={fv.div_fraction:.2f}  "
          f"copy={fv.copy_fraction:.2f}")
    print(f"    repeated_expr={fv.has_repeated_expr}  "
          f"copy_chains={fv.has_copy_chains}  "
          f"reg_pressure={fv.register_pressure:.2f}")

    print("\n[4] ADAPTIVE PASS EXECUTION (with Tabu Search & Rollback):")
    print(f"    {'Pass':<38} {'Decision':<14} {'ΔJ':>8}  {'Instrs':>6}→{'':<6} {'Cycles':>6}→")
    print(f"    {'─'*38} {'─'*14} {'─'*8}  {'─'*6} {'─'*6}  {'─'*6} {'─'*6}")

    for step in result.steps:
        decision = "✓ COMMIT " if step.accepted else "✗ ROLLBACK"
        delta = step.degradation_report.delta_j
        print(
            f"    {step.pass_name:<38} {decision:<14} {delta:>+8.3f}  "
            f"{step.metrics_before.instruction_count:>6}→{step.metrics_after.instruction_count:<6} "
            f"{step.metrics_before.estimated_cycle_cost:>6}→{step.metrics_after.estimated_cycle_cost:<6}"
        )

    print(f"\n    Rollbacks: {result.rollback_count}  |  "
          f"Tabu: {result.tabu_list if result.tabu_list else '(none)'}  |  "
          f"Converged: {'Yes' if result.converged else 'No'}")

    print("\n[5] FINAL OPTIMIZED TAC:")
    print(result.final_tac.dump())
    print(f"    → {result.final_metrics}")

    s = result.improvement_summary
    print("\n[6] QUANTITATIVE IMPROVEMENT REPORT:")
    print(f"    Instructions: {result.initial_metrics.instruction_count} → {result.final_metrics.instruction_count}  "
          f"(−{s['instructions_saved']} = {s['instruction_reduction_pct']:.1f}% reduction)")
    print(f"    ALU Cycles  : {result.initial_metrics.estimated_cycle_cost} → {result.final_metrics.estimated_cycle_cost}  "
          f"(−{s['cycles_saved']} = {s['cycle_reduction_pct']:.1f}% reduction)")
    sep()


def main():
    print_header()
    pipeline = OptiGuardPipeline(use_adaptive=True, max_budget=20)

    # Case 1: Canonical project spec example
    run_adaptive_case(
        pipeline, 1,
        "Canonical Phase-Ordering Benchmark",
        """
a = 10 * 2;
b = a + 0;
c = b;
"""
    )

    # Case 2: Mixed optimizations with CSE
    run_adaptive_case(
        pipeline, 2,
        "Dead Code + Identity + CSE",
        """
x = 10 + 5;
dead_val = 99 * 4;
y = x * 1;
z = y + 0;
final_res = z * 2;
"""
    )

    # Case 3: Strength reduction
    run_adaptive_case(
        pipeline, 3,
        "Strength Reduction Showcase",
        """
r1 = val * 2;
r2 = val * 4;
result = r1 + r2;
"""
    )

    # Case 4: Copy propagation chain
    run_adaptive_case(
        pipeline, 4,
        "Copy Propagation Chain",
        """
a = src;
b = a;
c = b;
result = c;
"""
    )

    # Case 5: Deep constant propagation
    run_adaptive_case(
        pipeline, 5,
        "Deep Constant Propagation",
        """
a = 5;
b = a + 3;
c = b * 2;
d = c - 1;
e = d + 0;
f = e;
"""
    )

    print("\nDemo complete. All optimization passes validated.\n")


if __name__ == "__main__":
    main()
