"""Strength Reduction Pass for OptiGuard.

Replaces expensive arithmetic operations with cheaper equivalents:
  - x * 2   →  x + x        (mul → add, saves ~2 cycles)
  - x * 1   →  x            (already in AlgebraicSimplification; safe to check again)
  - x ** 2  →  x * x        (power of 2 as repeated mul, if extended later)
  - x / 2.0 →  x * 0.5      (div → mul for power-of-two divisors)
  - x * 4   →  (x + x) + (x + x)  (strength reduce small integer multipliers)

This pass focuses on integer multipliers 2..8 and power-of-two divisors.
"""

from typing import Tuple
from optiguard.ir.tac import TACInstruction, TACProgram


class StrengthReductionPass:
    """Pass 5: Strength Reduction.

    Replaces costly multiplications and divisions with sequences of
    cheaper additions and multiplications where the result is equivalent.
    """

    name = "StrengthReduction"

    # Maximum integer multiplier for which we strength-reduce (avoid code bloat)
    MAX_MUL_FACTOR = 8

    def run(self, program: TACProgram) -> Tuple[TACProgram, bool]:
        modified = False
        new_program = TACProgram()
        temp_counter = self._find_max_temp(program) + 1

        def new_temp() -> str:
            nonlocal temp_counter
            name = f"t{temp_counter}"
            temp_counter += 1
            return name

        for instr in program.instructions:
            if not instr.is_binary():
                new_program.add(instr)
                continue

            op = instr.op
            arg1 = instr.arg1
            arg2 = instr.arg2
            result = instr.result

            reduced_instrs = None

            if op == '*':
                # Check if one operand is a small integer constant
                if self._is_small_int(arg2):
                    factor = int(self._to_number(arg2))
                    if factor == 2:
                        # x * 2 → x + x
                        reduced_instrs = [
                            TACInstruction(op='+', arg1=arg1, arg2=arg1, result=result)
                        ]
                    elif factor == 4:
                        # x * 4 → t = x + x; result = t + t
                        t = new_temp()
                        reduced_instrs = [
                            TACInstruction(op='+', arg1=arg1, arg2=arg1, result=t),
                            TACInstruction(op='+', arg1=t, arg2=t, result=result)
                        ]
                    elif factor == 8:
                        # x * 8 → t1 = x+x; t2 = t1+t1; result = t2+t2
                        t1 = new_temp()
                        t2 = new_temp()
                        reduced_instrs = [
                            TACInstruction(op='+', arg1=arg1, arg2=arg1, result=t1),
                            TACInstruction(op='+', arg1=t1, arg2=t1, result=t2),
                            TACInstruction(op='+', arg1=t2, arg2=t2, result=result)
                        ]
                elif self._is_small_int(arg1):
                    factor = int(self._to_number(arg1))
                    if factor == 2:
                        reduced_instrs = [
                            TACInstruction(op='+', arg1=arg2, arg2=arg2, result=result)
                        ]
                    elif factor == 4:
                        t = new_temp()
                        reduced_instrs = [
                            TACInstruction(op='+', arg1=arg2, arg2=arg2, result=t),
                            TACInstruction(op='+', arg1=t, arg2=t, result=result)
                        ]

            elif op == '/':
                # x / 2 → x * 0.5  (cheaper on most modern hardware due to avoiding idiv)
                if self._is_power_of_two_divisor(arg2):
                    divisor = self._to_number(arg2)
                    reciprocal = 1.0 / divisor
                    # Only reduce if reciprocal is a clean float (power-of-two)
                    reduced_instrs = [
                        TACInstruction(op='*', arg1=arg1, arg2=reciprocal, result=result)
                    ]

            if reduced_instrs:
                for ri in reduced_instrs:
                    new_program.add(ri)
                modified = True
            else:
                new_program.add(instr)

        return new_program, modified

    @staticmethod
    def _find_max_temp(program: TACProgram) -> int:
        max_idx = -1
        for instr in program.instructions:
            for var in list(instr.get_defs()) + list(instr.get_uses()):
                if var.startswith('t') and var[1:].isdigit():
                    max_idx = max(max_idx, int(var[1:]))
        return max_idx

    @staticmethod
    def _is_small_int(val) -> bool:
        try:
            n = float(str(val))
            return n == int(n) and 2 <= int(n) <= StrengthReductionPass.MAX_MUL_FACTOR and int(n) in (2, 4, 8)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_power_of_two_divisor(val) -> bool:
        try:
            n = float(str(val))
            if n != int(n) or n <= 0:
                return False
            n = int(n)
            return (n & (n - 1)) == 0 and 2 <= n <= 16
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _to_number(val):
        try:
            f = float(str(val))
            return int(f) if f == int(f) else f
        except (ValueError, TypeError):
            return 0
