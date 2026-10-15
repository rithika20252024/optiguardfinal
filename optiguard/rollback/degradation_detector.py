"""Optimization Degradation Detector for OptiGuard.

Defines the multi-objective cost function J(IR) used to determine
whether a proposed optimization actually improves the IR or degrades it.

Cost Function:
    J(IR) = w1 * instruction_count + w2 * estimated_cycle_cost + w3 * temp_count

A pass is ACCEPTED  if J(IR_new) < J(IR_prev)   (strict improvement)
A pass is REJECTED  if J(IR_new) >= J(IR_prev)   (no improvement or degradation)

Default weights (tunable):
    w1 = 1.0   # code size
    w2 = 0.5   # execution cycles (discounted to avoid over-weighting)
    w3 = 0.2   # register pressure (temporary variable count)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from optiguard.metrics.cost_evaluator import IRMetrics


# Default weight tuple (w1, w2, w3)
DEFAULT_WEIGHTS = (1.0, 0.5, 0.2)


@dataclass
class DegradationReport:
    """Result of a degradation check between two IR states."""
    j_before: float
    j_after: float
    delta_j: float            # j_after - j_before  (negative = improvement)
    degraded: bool
    message: str

    def __str__(self) -> str:
        tag = "⚠ DEGRADED" if self.degraded else "✓ ACCEPTED"
        return (
            f"[{tag}] J_prev={self.j_before:.3f}  J_new={self.j_after:.3f}  "
            f"ΔJ={self.delta_j:+.3f}  → {self.message}"
        )


class DegradationDetector:
    """Computes J(IR) and determines whether an optimization pass degraded the IR.

    Args:
        weights: Tuple (w1, w2, w3) controlling the importance of
                 instruction count, cycle cost, and temporary count.
    """

    def __init__(self, weights: tuple = DEFAULT_WEIGHTS) -> None:
        self.w1, self.w2, self.w3 = weights

    def cost(self, metrics: IRMetrics) -> float:
        """Compute the scalar cost J(IR) from an IRMetrics snapshot."""
        return (
            self.w1 * metrics.instruction_count
            + self.w2 * metrics.estimated_cycle_cost
            + self.w3 * metrics.temporary_count
        )

    def check(self, before: IRMetrics, after: IRMetrics) -> DegradationReport:
        """Compare J(IR_before) and J(IR_after) and return a DegradationReport.

        A pass is considered degrading if J_after >= J_before (no strict improvement).
        """
        j_before = self.cost(before)
        j_after = self.cost(after)
        delta = j_after - j_before
        degraded = delta >= 0.0

        if degraded:
            msg = "Pass caused NO improvement — triggering rollback."
        else:
            msg = f"Pass improved IR by ΔJ={delta:.3f} — committing."

        return DegradationReport(
            j_before=j_before,
            j_after=j_after,
            delta_j=delta,
            degraded=degraded,
            message=msg,
        )
