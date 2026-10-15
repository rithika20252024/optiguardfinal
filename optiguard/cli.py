"""OptiGuard CLI — Command-line interface for the adaptive optimizer."""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optiguard.pipeline import OptiGuardPipeline
from optiguard.profiler.feature_profiler import FeatureProfiler


def main():
    parser = argparse.ArgumentParser(
        prog="optiguard",
        description="OptiGuard: Adaptive Compiler Optimization with Degradation Detection"
    )
    parser.add_argument(
        "source", nargs="?", default=None,
        help="Path to source file (C-subset). If omitted, reads from stdin."
    )
    parser.add_argument(
        "--sequential", action="store_true",
        help="Use sequential (non-adaptive) pass ordering instead of adaptive."
    )
    parser.add_argument(
        "--budget", type=int, default=20,
        help="Maximum number of accepted optimization passes (default: 20)."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed per-pass step trace."
    )
    parser.add_argument(
        "--features", action="store_true",
        help="Print the IR feature vector before optimization."
    )
    args = parser.parse_args()

    # Read source code
    if args.source:
        try:
            with open(args.source, 'r') as f:
                source = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.source}' not found.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Reading source from stdin (Ctrl+D when done)...")
        source = sys.stdin.read()

    pipeline = OptiGuardPipeline(
        use_adaptive=not args.sequential,
        max_budget=args.budget
    )

    result = pipeline.optimize(source)

    # Print feature vector if requested
    if args.features:
        fv = FeatureProfiler.profile(result.initial_tac)
        print("\n=== IR Feature Vector ===")
        print(fv)

    # Initial TAC
    print("\n=== Initial TAC ===")
    print(result.initial_tac.dump())
    print(f"  {result.initial_metrics}")

    # Pass trace
    if args.verbose:
        print("\n=== Optimization Passes ===")
        for i, step in enumerate(result.steps, 1):
            status = "✓ COMMIT" if step.accepted else "✗ ROLLBACK"
            print(f"  [{i:2d}] {step.pass_name:<38} {status}  ΔJ={step.degradation_report.delta_j:+.3f}")

    # Final TAC
    print("\n=== Optimized TAC ===")
    print(result.final_tac.dump())
    print(f"  {result.final_metrics}")

    # Summary
    s = result.improvement_summary
    print(f"\n=== Summary ===")
    print(f"  Instructions : {result.initial_metrics.instruction_count} → {result.final_metrics.instruction_count}  ({s['instruction_reduction_pct']:.1f}% reduction)")
    print(f"  ALU Cycles   : {result.initial_metrics.estimated_cycle_cost} → {result.final_metrics.estimated_cycle_cost}  ({s['cycle_reduction_pct']:.1f}% reduction)")
    print(f"  Rollbacks    : {result.rollback_count}")
    print(f"  Converged    : {'Yes' if result.converged else 'No'}")
    if result.tabu_list:
        print(f"  Tabu list    : {result.tabu_list}")


if __name__ == "__main__":
    main()
