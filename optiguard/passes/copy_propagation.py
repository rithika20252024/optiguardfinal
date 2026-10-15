"""Copy Propagation Pass for OptiGuard.

When a copy instruction  `y = x`  exists and `x` is not subsequently
redefined before `y` is used, all uses of `y` are replaced by `x`,
enabling later dead-code elimination to remove the copy instruction.
"""

from typing import Dict, Optional, Tuple
from optiguard.ir.tac import TACInstruction, TACProgram


class CopyPropagationPass:
    """Pass 6: Copy Propagation.

    Maintains a copy table mapping  dest → src  for simple copy
    instructions.  Any subsequent use of *dest* is replaced by *src*
    (propagated forward) as long as *src* has not been redefined.

    After propagation, redundant copy instructions (`y = x` where
    all uses of `y` have been replaced) are left for DCE to remove.
    """

    name = "CopyPropagation"

    def run(self, program: TACProgram) -> Tuple[TACProgram, bool]:
        modified = False
        new_program = TACProgram()

        # Maps variable -> its current copy-source (or None if not a simple copy)
        copy_table: Dict[str, str] = {}

        def _resolve(val) -> object:
            """Resolve a value through the copy table (once)."""
            if isinstance(val, str) and val in copy_table:
                return copy_table[val]
            return val

        def _invalidate(var: str) -> None:
            """Remove var from table as source or dest when it is redefined."""
            copy_table.pop(var, None)
            # Also remove entries where var is the source (it's been clobbered)
            stale = [k for k, v in copy_table.items() if v == var]
            for k in stale:
                del copy_table[k]

        for instr in program.instructions:
            new_arg1 = _resolve(instr.arg1)
            new_arg2 = _resolve(instr.arg2)

            # Detect if propagation actually changed anything
            if new_arg1 != instr.arg1 or new_arg2 != instr.arg2:
                modified = True

            new_instr = TACInstruction(
                op=instr.op,
                arg1=new_arg1,
                arg2=new_arg2,
                result=instr.result
            )

            # Invalidate stale copies for the destination variable
            _invalidate(instr.result)

            # Record copy relationship if this is a simple copy from a variable
            if new_instr.is_copy() and isinstance(new_instr.arg1, str):
                copy_table[instr.result] = new_instr.arg1

            new_program.add(new_instr)

        return new_program, modified
