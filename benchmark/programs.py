"""Benchmark Programs Library for OptiGuard.

Each program is a C-subset source string used to evaluate OptiGuard's
optimization effectiveness across a range of real-world code patterns.
"""

BENCHMARK_PROGRAMS = [
    {
        "name": "B1: Constant Arithmetic Chain",
        "description": "Pure constant arithmetic that should fold completely",
        "source": """
a = 10 * 2;
b = a + 0;
c = b;
"""
    },
    {
        "name": "B2: Dead Code + Multi-Pass",
        "description": "Dead temporaries + identity simplifications",
        "source": """
x = 10 + 5;
dead_val = 99 * 4;
y = x * 1;
z = y + 0;
final_res = z * 2;
"""
    },
    {
        "name": "B3: Symbolic Identity Elimination",
        "description": "Variable-based algebraic identity reduction",
        "source": """
temp_a = input_val * 1;
temp_b = temp_a + 0;
res = temp_b;
"""
    },
    {
        "name": "B4: Common Sub-expression",
        "description": "Repeated arithmetic sub-expressions (CSE candidate)",
        "source": """
a = x + y;
b = x + y;
c = a * 2;
d = b * 2;
"""
    },
    {
        "name": "B5: Strength Reduction Targets",
        "description": "Multiplications by 2, 4, 8 eligible for strength reduction",
        "source": """
r1 = val * 2;
r2 = val * 4;
r3 = val * 8;
"""
    },
    {
        "name": "B6: Copy Propagation Chain",
        "description": "Chain of copy assignments that propagation can collapse",
        "source": """
a = src;
b = a;
c = b;
result = c;
"""
    },
    {
        "name": "B7: Mixed Optimization Benchmark",
        "description": "Realistic mix: constants, dead code, identities, copies",
        "source": """
t = 3 * 4;
u = t + 0;
v = 100 * 0;
w = v + u;
dead = 9 * 9;
result = w * 1;
"""
    },
    {
        "name": "B8: Deep Constant Propagation",
        "description": "Long constant propagation chain across many assignments",
        "source": """
a = 5;
b = a + 3;
c = b * 2;
d = c - 1;
e = d + 0;
f = e;
"""
    },
]
