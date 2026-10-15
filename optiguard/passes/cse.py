"""Common Sub-expression Elimination (CSE) Pass for OptiGuard.

Detects and eliminates redundant computations of the same binary expression.
If (op, arg1, arg2) has been computed before and neither operand has been
redefined since, the result is reused directly.
"""

from typing import Dict, Optional, Tuple, Set
from optiguard.ir.tac import TACInstruction, TACProgram


class CSEPass:
    """Pass 4: Common Sub-expression Elimination.

    Scans forward through the TAC and maintains an available-expressions table.
    When the same (op, arg1, arg2) expression is encountered a second time
    and its operands are still valid, replaces the recomputation with a copy
    from the previously computed result.
    """

    name = "CommonSubexpressionElimination"

    def run(self, program: TACProgram) -> Tuple[TACProgram, bool]:
        modified = False
        new_program = TACProgram()

        # Maps (op, arg1, arg2) -> variable that already holds this result
        available: Dict[Tuple, str] = {}

        # Track which variables have been (re)defined so we can invalidate stale entries
        def _invalidate(var: str) -> None:
            to_remove = [k for k, v in available.items() if v == var or var in k]
            for k in to_remove:
                del available[k]

        for instr in program.instructions:
            if instr.is_binary():
                key = (instr.op, instr.arg1, instr.arg2)
                # Commutative variants (+, *)
                key_comm = (instr.op, instr.arg2, instr.arg1) if instr.op in ('+', '*') else None

                prev_result = available.get(key) or (key_comm and available.get(key_comm))

                if prev_result and prev_result != instr.result:
                    # Replace binary op with copy from previously computed result
                    new_instr = TACInstruction(op=None, arg1=prev_result, arg2=None, result=instr.result)
                    new_program.add(new_instr)
                    # Map the new result to the same value as well
                    available[(instr.op, instr.arg1, instr.arg2)] = prev_result
                    available[(instr.op, instr.arg2, instr.arg1)] = prev_result if instr.op in ('+', '*') else available.get((instr.op, instr.arg2, instr.arg1), prev_result)
                    modified = True
                    continue
                else:
                    # Record this expression as available
                    _invalidate(instr.result)
                    available[key] = instr.result
                    if key_comm:
                        available[key_comm] = instr.result
            else:
                # Copy / assignment: invalidate the result variable's expressions
                _invalidate(instr.result)

            new_program.add(TACInstruction(
                op=instr.op,
                arg1=instr.arg1,
                arg2=instr.arg2,
                result=instr.result
            ))

        return new_program, modified
