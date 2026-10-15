#!/usr/bin/env python3
"""OptiGuard Automated Benchmark Suite.

Runs all benchmark programs through the adaptive OptiGuard pipeline
and prints a formatted summary table of optimization results.

Usage:
    python3 benchmark/run_benchmarks.py
    python3 benchmark/run_benchmarks.py --sequential   # compare legacy mode
"""

import sys
import os
import argparse

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optiguard.pipeline import OptiGuardPipeline
from benchmark.programs import BENCHMARK_PROGRAMS


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║          OptiGuard Benchmark Suite — Adaptive Optimization Engine       ║
║          Phase-Ordering + Degradation Detection + Safe Rollback         ║
╚══════════════════════════════════════════════════════════════════════════╝
""")


def run_benchmarks(use_adaptive: bool = True):
    mode_label = "ADAPTIVE (with Rollback)" if use_adaptive else "SEQUENTIAL (Baseline)"
    print(f"Mode: {mode_label}\n")

    pipeline = OptiGuardPipeline(use_adaptive=use_adaptive)

    results = []
    for bm in BENCHMARK_PROGRAMS:
        try:
            result = pipeline.optimize(bm["source"])
            results.append({
                "name": bm["name"],
                "desc": bm["description"],
                "instr_before": result.initial_metrics.instruction_count,
                "instr_after": result.final_metrics.instruction_count,
                "cycles_before": result.initial_metrics.estimated_cycle_cost,
                "cycles_after": result.final_metrics.estimated_cycle_cost,
                "instr_pct": result.improvement_summary["instruction_reduction_pct"],
                "cycle_pct": result.improvement_summary["cycle_reduction_pct"],
                "rollbacks": result.rollback_count,
                "passes_applied": len([s for s in result.steps if s.accepted]),
                "tabu": ", ".join(result.tabu_list) if result.tabu_list else "—",
                "converged": "✓" if result.converged else "…",
            })
        except Exception as e:
            results.append({
                "name": bm["name"],
                "desc": bm["description"],
                "error": str(e),
            })

    # ------------------------------------------------------------------ #
    # Print results table
    # ------------------------------------------------------------------ #
    col_widths = {
        "name": 34, "instr": 8, "cycles": 8, "ipct": 8, "cpct": 8,
        "rb": 5, "passes": 6, "conv": 5
    }

    header = (
        f"{'Benchmark':<34} {'Instr':>8} {'Instr':>8} {'%Instr':>8} "
        f"{'Cyc':>8} {'Cyc':>8} {'%Cyc':>8} {'RB':>5} {'PA':>6} {'C':>5}"
    )
    subhdr = (
        f"{'':34} {'Before':>8} {'After':>8} {'Saved':>8} "
        f"{'Before':>8} {'After':>8} {'Saved':>8} {'':>5} {'':>6} {'':>5}"
    )

    sep = "─" * 100

    print(sep)
    print(header)
    print(subhdr)
    print(sep)

    total_instr_saved = 0
    total_cycle_saved = 0
    valid_count = 0

    for r in results:
        if "error" in r:
            print(f"{'[ERROR] ' + r['name']:<34}  {r['error']}")
            continue
        valid_count += 1
        total_instr_saved += r["instr_before"] - r["instr_after"]
        total_cycle_saved += r["cycles_before"] - r["cycles_after"]
        print(
            f"{r['name']:<34} "
            f"{r['instr_before']:>8d} {r['instr_after']:>8d} {r['instr_pct']:>7.1f}% "
            f"{r['cycles_before']:>8d} {r['cycles_after']:>8d} {r['cycle_pct']:>7.1f}% "
            f"{r['rollbacks']:>5d} {r['passes_applied']:>6d} {r['converged']:>5}"
        )

    print(sep)
    if valid_count > 0:
        print(f"  Total Instructions Saved  : {total_instr_saved}")
        print(f"  Total Cycle Cost Saved    : {total_cycle_saved}")
        print(f"  Benchmarks Completed      : {valid_count}/{len(BENCHMARK_PROGRAMS)}")
    print()

    # ------------------------------------------------------------------ #
    # Detailed per-benchmark step trace
    # ------------------------------------------------------------------ #
    print("\n══ DETAILED PASS TRACES ══\n")
    for bm in BENCHMARK_PROGRAMS:
        try:
            result = pipeline.optimize(bm["source"])
            print(f"  ▸ {bm['name']}")
            for i, step in enumerate(result.steps, 1):
                status = "✓ ACCEPTED" if step.accepted else "✗ ROLLBACK"
                print(f"      [{i:2d}] {step.pass_name:<35} {status}  "
                      f"ΔJ={step.degradation_report.delta_j:+.3f}")
            print()
        except Exception as e:
            print(f"  ▸ {bm['name']}: ERROR — {e}\n")


def main():
    parser = argparse.ArgumentParser(description="OptiGuard Benchmark Runner")
    parser.add_argument("--sequential", action="store_true",
                        help="Run in sequential (baseline) mode without adaptive rollback")
    parser.add_argument("--compare", action="store_true",
                        help="Run both modes and compare side-by-side")
    args = parser.parse_args()

    print_banner()

    if args.compare:
        print("═" * 100)
        print(" ADAPTIVE MODE")
        print("═" * 100)
        run_benchmarks(use_adaptive=True)
        print("\n" + "═" * 100)
        print(" SEQUENTIAL (BASELINE) MODE")
        print("═" * 100)
        run_benchmarks(use_adaptive=False)
    else:
        run_benchmarks(use_adaptive=not args.sequential)


if __name__ == "__main__":
    main()
