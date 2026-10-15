"""Optimization Pipeline Driver for OptiGuard — Adaptive Version.

This module implements the full OptiGuard optimization pipeline including:

  1. Frontend (Lexer → Parser → AST → TAC IR generation)
  2. IR Feature Extraction (FeatureProfiler)
  3. Adaptive Pass Selection (AdaptivePassSelector with Tabu Search)
  4. Transactional Snapshot & Rollback (SnapshotStack)
  5. Degradation Detection (DegradationDetector, J(IR) cost function)
  6. Convergence & Budget Control

Pipeline Loop:
    while budget_remaining and not converged:
        features  = FeatureProfiler.profile(current_ir)
        pass      = AdaptiveSelector.select(features)
        if pass is None: break  # all passes exhausted → convergence
        SnapshotStack.push(current_ir)
        new_ir, modified = pass.run(current_ir)
        report = DegradationDetector.check(J_prev, J_new)
        if report.degraded or not modified:
            current_ir = SnapshotStack.pop()   # ROLLBACK
            AdaptiveSelector.add_to_tabu(pass.name)
        else:
            SnapshotStack.commit()             # ACCEPT
            current_ir = new_ir
            budget -= 1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from optiguard.frontend.lexer import Lexer
from optiguard.frontend.parser import Parser
from optiguard.ir.ir_generator import IRGenerator
from optiguard.ir.tac import TACProgram
from optiguard.passes.constant_folding import ConstantFoldingPass
from optiguard.passes.algebraic_simplification import AlgebraicSimplificationPass
from optiguard.passes.dead_code_elimination import DeadCodeEliminationPass
from optiguard.passes.cse import CSEPass
from optiguard.passes.strength_reduction import StrengthReductionPass
from optiguard.passes.copy_propagation import CopyPropagationPass
from optiguard.metrics.cost_evaluator import CostEvaluator, IRMetrics
from optiguard.profiler.feature_profiler import FeatureProfiler, FeatureVector
from optiguard.rollback.snapshot_stack import SnapshotStack
from optiguard.rollback.degradation_detector import DegradationDetector, DegradationReport
from optiguard.search.adaptive_selector import AdaptivePassSelector


@dataclass
class PassStepRecord:
    """Record of a single pass application attempt."""
    pass_name: str
    modified: bool
    accepted: bool              # False if rolled back
    rollback: bool              # True if snapshot was restored
    metrics_before: IRMetrics
    metrics_after: IRMetrics
    degradation_report: DegradationReport
    tac_snapshot: TACProgram    # IR state AFTER this step (post-commit or post-rollback)
    features_before: FeatureVector


@dataclass
class OptimizationResult:
    """Full result of the OptiGuard optimization pipeline."""
    source_code: str
    initial_tac: TACProgram
    initial_metrics: IRMetrics
    final_tac: TACProgram
    final_metrics: IRMetrics
    steps: List[PassStepRecord] = field(default_factory=list)
    improvement_summary: Dict[str, Any] = field(default_factory=dict)
    rollback_count: int = 0
    tabu_list: List[str] = field(default_factory=list)
    converged: bool = False


class OptiGuardPipeline:
    """Adaptive compiler optimization pipeline with degradation detection and rollback.

    Args:
        max_budget:  Maximum number of ACCEPTED optimization passes per run.
        weights:     (w1, w2, w3) cost-function weights for DegradationDetector.
        use_adaptive: If True (default), uses adaptive selection + rollback.
                      If False, falls back to the original sequential fixed-order mode.
    """

    DEFAULT_PASSES = [
        ConstantFoldingPass(),
        AlgebraicSimplificationPass(),
        DeadCodeEliminationPass(),
        CSEPass(),
        StrengthReductionPass(),
        CopyPropagationPass(),
    ]

    def __init__(
        self,
        max_budget: int = 20,
        weights: tuple = (1.0, 0.5, 0.2),
        use_adaptive: bool = True,
    ) -> None:
        self.passes = self.DEFAULT_PASSES
        self.max_budget = max_budget
        self.use_adaptive = use_adaptive
        self._detector = DegradationDetector(weights=weights)
        self._selector = AdaptivePassSelector(self.passes)
        self._snapshot_stack = SnapshotStack()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def compile_source(self, source_code: str) -> TACProgram:
        """Run the frontend: Lexer → Parser → AST → TAC IR."""
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        ir_gen = IRGenerator()
        return ir_gen.generate(ast)

    def optimize(self, source_code: str) -> OptimizationResult:
        """Execute the full optimization pipeline and return structured results."""
        initial_tac = self.compile_source(source_code)
        initial_metrics = CostEvaluator.evaluate(initial_tac)

        if self.use_adaptive:
            return self._adaptive_optimize(source_code, initial_tac, initial_metrics)
        else:
            return self._sequential_optimize(source_code, initial_tac, initial_metrics)

    # ------------------------------------------------------------------ #
    #  Adaptive Pipeline (full OptiGuard algorithm)                       #
    # ------------------------------------------------------------------ #

    def _adaptive_optimize(
        self,
        source_code: str,
        initial_tac: TACProgram,
        initial_metrics: IRMetrics,
    ) -> OptimizationResult:
        """Adaptive optimization loop with tabu search and transactional rollback."""

        self._selector.reset_tabu()
        self._snapshot_stack.clear()

        current_tac = initial_tac.clone()
        current_metrics = initial_metrics
        step_records: List[PassStepRecord] = []
        rollback_count = 0
        budget_remaining = self.max_budget

        while budget_remaining > 0:
            # 1. Extract features from current IR
            features = FeatureProfiler.profile(current_tac)

            # 2. Select next pass (adaptive / tabu-aware)
            opt_pass = self._selector.select(features)
            if opt_pass is None:
                # All passes exhausted → convergence
                break

            # 3. Checkpoint
            self._snapshot_stack.push(current_tac)
            metrics_before = current_metrics

            # 4. Apply pass
            new_tac, modified = opt_pass.run(current_tac)
            new_metrics = CostEvaluator.evaluate(new_tac)

            # 5. Degradation check
            report = self._detector.check(metrics_before, new_metrics)

            if report.degraded or not modified:
                # ROLLBACK
                current_tac = self._snapshot_stack.pop()
                current_metrics = metrics_before
                self._selector.add_to_tabu(opt_pass.name)
                rollback_count += 1
                accepted = False
            else:
                # COMMIT
                self._snapshot_stack.commit()
                current_tac = new_tac
                current_metrics = new_metrics
                budget_remaining -= 1
                accepted = True

            step_records.append(PassStepRecord(
                pass_name=opt_pass.name,
                modified=modified,
                accepted=accepted,
                rollback=not accepted,
                metrics_before=metrics_before,
                metrics_after=new_metrics,
                degradation_report=report,
                tac_snapshot=current_tac.clone(),
                features_before=features,
            ))

            # 6. Convergence: if all passes are in tabu, stop
            if self._selector.all_exhausted():
                break

        final_metrics = CostEvaluator.evaluate(current_tac)
        summary = CostEvaluator.calculate_improvement(initial_metrics, final_metrics)

        return OptimizationResult(
            source_code=source_code,
            initial_tac=initial_tac,
            initial_metrics=initial_metrics,
            final_tac=current_tac,
            final_metrics=final_metrics,
            steps=step_records,
            improvement_summary=summary,
            rollback_count=rollback_count,
            tabu_list=list(self._selector.tabu_list),
            converged=self._selector.all_exhausted() or budget_remaining == 0,
        )

    # ------------------------------------------------------------------ #
    #  Sequential Pipeline (legacy / baseline mode)                       #
    # ------------------------------------------------------------------ #

    def _sequential_optimize(
        self,
        source_code: str,
        initial_tac: TACProgram,
        initial_metrics: IRMetrics,
    ) -> OptimizationResult:
        """Original sequential fixed-order pass execution (no rollback)."""
        current_tac = initial_tac.clone()
        step_records: List[PassStepRecord] = []

        baseline_passes = [
            ConstantFoldingPass(),
            AlgebraicSimplificationPass(),
            DeadCodeEliminationPass(),
        ]

        for opt_pass in baseline_passes:
            metrics_before = CostEvaluator.evaluate(current_tac)
            features = FeatureProfiler.profile(current_tac)
            new_tac, modified = opt_pass.run(current_tac)
            metrics_after = CostEvaluator.evaluate(new_tac)
            report = self._detector.check(metrics_before, metrics_after)

            step_records.append(PassStepRecord(
                pass_name=opt_pass.name,
                modified=modified,
                accepted=True,
                rollback=False,
                metrics_before=metrics_before,
                metrics_after=metrics_after,
                degradation_report=report,
                tac_snapshot=new_tac.clone(),
                features_before=features,
            ))
            current_tac = new_tac

        final_metrics = CostEvaluator.evaluate(current_tac)
        summary = CostEvaluator.calculate_improvement(initial_metrics, final_metrics)

        return OptimizationResult(
            source_code=source_code,
            initial_tac=initial_tac,
            initial_metrics=initial_metrics,
            final_tac=current_tac,
            final_metrics=final_metrics,
            steps=step_records,
            improvement_summary=summary,
            rollback_count=0,
            tabu_list=[],
            converged=True,
        )
