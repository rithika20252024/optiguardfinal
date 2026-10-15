"""Adaptive Pass Selector with Tabu Search for OptiGuard.

The AdaptiveSelector examines the current IR FeatureVector and selects
the next most-promising optimization pass to apply, excluding passes
already on the Tabu List (passes that previously caused degradation or
yielded no improvement on this IR).

Selection Heuristic (Priority Score):

Each pass is scored based on how well its characteristics match the
current IR features:

  ConstantFolding      → high score when constant_density > 0.3
  AlgebraicSimpl.      → high score when constant_density > 0 and add_sub_fraction > 0
  DeadCodeElim.        → high score when temp_density > 0.3
  CSE                  → high score when has_repeated_expr == 1
  StrengthReduction    → high score when mul_fraction > 0 or div_fraction > 0
  CopyPropagation      → high score when copy_fraction > 0.3 or has_copy_chains

If all candidate passes are in the tabu list, `select` returns None,
signalling convergence.
"""

from __future__ import annotations

from typing import List, Optional, Set, TYPE_CHECKING
from optiguard.profiler.feature_profiler import FeatureVector

if TYPE_CHECKING:
    from optiguard.ir.tac import TACProgram


class AdaptivePassSelector:
    """Selects the best next pass to apply based on IR features and a tabu list.

    Args:
        passes: Ordered list of pass instances (all available passes).
    """

    def __init__(self, passes: list) -> None:
        self._passes = passes
        self._tabu: Set[str] = set()

    def reset_tabu(self) -> None:
        """Clear the tabu list (called at the start of a fresh optimization run)."""
        self._tabu.clear()

    def add_to_tabu(self, pass_name: str) -> None:
        """Add a pass name to the tabu list after it caused degradation."""
        self._tabu.add(pass_name)

    @property
    def tabu_list(self) -> Set[str]:
        return frozenset(self._tabu)

    def select(self, features: FeatureVector) -> Optional[object]:
        """Return the best non-tabu pass for the current feature vector, or None.

        Args:
            features: FeatureVector from the current IR state.

        Returns:
            A pass instance, or None if all passes are in the tabu list.
        """
        candidates = [p for p in self._passes if p.name not in self._tabu]
        if not candidates:
            return None

        scored = [(self._score(p, features), p) for p in candidates]
        scored.sort(key=lambda x: -x[0])  # highest score first
        best_score, best_pass = scored[0]
        return best_pass if best_score > 0 else candidates[0]

    @staticmethod
    def _score(opt_pass, fv: FeatureVector) -> float:
        """Compute a heuristic priority score for *opt_pass* given *fv*."""
        name = opt_pass.name
        score = 0.0

        if name == "ConstantFolding":
            # Useful when there are constant operands or binary ops with constants
            score = fv.constant_density * 3.0 + fv.has_binary_ops * 0.5

        elif name == "AlgebraicSimplification":
            # Useful when there are add/sub ops that may simplify with 0 or mul by 1
            score = fv.add_sub_fraction * 2.0 + fv.constant_density * 1.5

        elif name == "DeadCodeElimination":
            # Useful when there are many temporaries (high temp_density = likely dead)
            score = fv.temp_density * 3.0 + fv.copy_fraction * 1.0

        elif name == "CommonSubexpressionElimination":
            # Only meaningful if repeated expressions exist
            binary_ops = (fv.add_sub_fraction + fv.mul_fraction + fv.div_fraction) * 0.5
            score = fv.has_repeated_expr * 5.0 + binary_ops

        elif name == "StrengthReduction":
            # Useful when there are multiplications or divisions
            score = fv.mul_fraction * 3.0 + fv.div_fraction * 4.0

        elif name == "CopyPropagation":
            # Useful when copy chains or high copy fraction
            score = fv.copy_fraction * 2.5 + fv.has_copy_chains * 3.0

        return score

    def all_exhausted(self) -> bool:
        """Return True if every known pass is in the tabu list."""
        return all(p.name in self._tabu for p in self._passes)
