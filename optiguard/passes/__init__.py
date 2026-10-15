"""OptiGuard Passes Package."""

from optiguard.passes.constant_folding import ConstantFoldingPass
from optiguard.passes.algebraic_simplification import AlgebraicSimplificationPass
from optiguard.passes.dead_code_elimination import DeadCodeEliminationPass
from optiguard.passes.cse import CSEPass
from optiguard.passes.strength_reduction import StrengthReductionPass
from optiguard.passes.copy_propagation import CopyPropagationPass

ALL_PASSES = [
    ConstantFoldingPass,
    AlgebraicSimplificationPass,
    DeadCodeEliminationPass,
    CSEPass,
    StrengthReductionPass,
    CopyPropagationPass,
]

__all__ = [
    "ConstantFoldingPass",
    "AlgebraicSimplificationPass",
    "DeadCodeEliminationPass",
    "CSEPass",
    "StrengthReductionPass",
    "CopyPropagationPass",
    "ALL_PASSES",
]
