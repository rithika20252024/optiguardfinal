"""IR Feature Profiler for OptiGuard Adaptive Pass Selection.

Extracts a structured feature vector from a TACProgram to guide
the adaptive pass selector.  All features are normalised to [0, 1]
where meaningful, so they are scale-invariant.

Feature Vector (FeatureVector dataclass):
  - instruction_count    : raw number of TAC instructions
  - temp_density         : fraction of instructions that produce temporaries
  - add_sub_fraction     : fraction of binary ops that are +/-
  - mul_fraction         : fraction of binary ops that are *
  - div_fraction         : fraction of binary ops that are /
  - copy_fraction        : fraction of instructions that are copies
  - constant_density     : fraction of operands that are numeric constants
  - distinct_variables   : raw count of distinct variable names
  - register_pressure    : estimated live-range overlap (temporaries / total vars)
  - has_binary_ops       : 1 if any binary op exists, else 0
  - has_copy_chains      : 1 if any chain a→b→c copies detected, else 0
  - has_repeated_expr    : 1 if any (op, arg1, arg2) key appears > once, else 0
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Set
from optiguard.ir.tac import TACProgram


@dataclass
class FeatureVector:
    """Normalised feature vector describing the current IR state."""
    instruction_count: int = 0
    temp_density: float = 0.0
    add_sub_fraction: float = 0.0
    mul_fraction: float = 0.0
    div_fraction: float = 0.0
    copy_fraction: float = 0.0
    constant_density: float = 0.0
    distinct_variables: int = 0
    register_pressure: float = 0.0
    has_binary_ops: int = 0
    has_copy_chains: int = 0
    has_repeated_expr: int = 0

    def as_dict(self) -> Dict:
        return asdict(self)

    def __str__(self) -> str:
        d = self.as_dict()
        parts = [f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}" for k, v in d.items()]
        return "FeatureVector(" + ", ".join(parts) + ")"


class FeatureProfiler:
    """Extracts a FeatureVector from a TACProgram for adaptive pass selection."""

    @classmethod
    def profile(cls, program: TACProgram) -> FeatureVector:
        instrs = program.instructions
        n = len(instrs)
        if n == 0:
            return FeatureVector()

        # Counters
        temp_defs = 0
        binary_count = 0
        add_sub_count = 0
        mul_count = 0
        div_count = 0
        copy_count = 0
        constant_operands = 0
        total_operands = 0

        all_vars: Set[str] = set()
        all_temps: Set[str] = set()

        # For CSE / copy-chain detection
        expr_seen: Dict = {}
        repeated_expr = False
        copy_srcs: Dict[str, str] = {}   # dest -> src for simple copies
        copy_chain = False

        for instr in instrs:
            # Collect variables
            for v in instr.get_defs() | instr.get_uses():
                all_vars.add(v)
                if v.startswith('t') and v[1:].isdigit():
                    all_temps.add(v)

            result = instr.result
            if result.startswith('t') and result[1:].isdigit():
                temp_defs += 1

            if instr.is_binary():
                binary_count += 1
                op = instr.op
                if op in ('+', '-'):
                    add_sub_count += 1
                elif op == '*':
                    mul_count += 1
                elif op == '/':
                    div_count += 1

                # CSE detection
                key = (op, instr.arg1, instr.arg2)
                key_c = (op, instr.arg2, instr.arg1) if op in ('+', '*') else None
                if key in expr_seen or (key_c and key_c in expr_seen):
                    repeated_expr = True
                else:
                    expr_seen[key] = result

                # Operand analysis
                for operand in (instr.arg1, instr.arg2):
                    total_operands += 1
                    if isinstance(operand, (int, float)):
                        constant_operands += 1
                    elif isinstance(operand, str):
                        try:
                            float(operand)
                            constant_operands += 1
                        except ValueError:
                            pass

            else:
                # Copy instruction
                copy_count += 1
                if isinstance(instr.arg1, str):
                    # Check for chain: a = b, c = a
                    if instr.arg1 in copy_srcs:
                        copy_chain = True
                    copy_srcs[result] = instr.arg1
                total_operands += 1
                if isinstance(instr.arg1, (int, float)):
                    constant_operands += 1
                elif isinstance(instr.arg1, str):
                    try:
                        float(instr.arg1)
                        constant_operands += 1
                    except ValueError:
                        pass

        num_vars = max(len(all_vars), 1)
        num_temps = len(all_temps)
        const_density = constant_operands / max(total_operands, 1)
        reg_pressure = num_temps / num_vars

        return FeatureVector(
            instruction_count=n,
            temp_density=temp_defs / n,
            add_sub_fraction=add_sub_count / n,
            mul_fraction=mul_count / n,
            div_fraction=div_count / n,
            copy_fraction=copy_count / n,
            constant_density=const_density,
            distinct_variables=len(all_vars),
            register_pressure=reg_pressure,
            has_binary_ops=1 if binary_count > 0 else 0,
            has_copy_chains=1 if copy_chain else 0,
            has_repeated_expr=1 if repeated_expr else 0,
        )
