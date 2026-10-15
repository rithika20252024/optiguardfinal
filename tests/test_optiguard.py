"""Comprehensive Unit Tests for OptiGuard — Full 100% Implementation.

Tests covered:
  Frontend: Lexer tokenization, Parser AST construction
  IR: TAC generation, clone/snapshot integrity
  Passes: ConstantFolding, AlgebraicSimplification, DeadCodeElimination,
          CSE, StrengthReduction, CopyPropagation
  Rollback Engine: SnapshotStack push/pop/commit, DegradationDetector
  Profiler: FeatureVector extraction
  Search: AdaptivePassSelector tabu logic
  Pipeline: End-to-end canonical, adaptive loop, rollback event detection
  Benchmarks: All 8 benchmark programs run without error
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optiguard.frontend.lexer import Lexer, TokenType
from optiguard.frontend.parser import Parser
from optiguard.frontend.ast_nodes import ProgramNode, AssignNode, BinaryOpNode
from optiguard.ir.ir_generator import IRGenerator
from optiguard.ir.tac import TACInstruction, TACProgram
from optiguard.passes.constant_folding import ConstantFoldingPass
from optiguard.passes.algebraic_simplification import AlgebraicSimplificationPass
from optiguard.passes.dead_code_elimination import DeadCodeEliminationPass
from optiguard.passes.cse import CSEPass
from optiguard.passes.strength_reduction import StrengthReductionPass
from optiguard.passes.copy_propagation import CopyPropagationPass
from optiguard.rollback.snapshot_stack import SnapshotStack
from optiguard.rollback.degradation_detector import DegradationDetector
from optiguard.profiler.feature_profiler import FeatureProfiler
from optiguard.search.adaptive_selector import AdaptivePassSelector
from optiguard.pipeline import OptiGuardPipeline
from optiguard.metrics.cost_evaluator import CostEvaluator, IRMetrics


# ─────────────────────────────────────────────────────────
# Helper: compile source to TAC
# ─────────────────────────────────────────────────────────
def compile_src(source: str) -> TACProgram:
    pipeline = OptiGuardPipeline()
    return pipeline.compile_source(source)


# ══════════════════════════════════════════════════════════
# 1. FRONTEND TESTS
# ══════════════════════════════════════════════════════════
class TestFrontend(unittest.TestCase):

    def test_lexer_basic_tokens(self):
        code = "a = 10 * 2;"
        tokens = Lexer(code).tokenize()
        types = [t.type for t in tokens]
        expected = [
            TokenType.IDENTIFIER, TokenType.ASSIGN, TokenType.NUMBER,
            TokenType.MUL, TokenType.NUMBER, TokenType.SEMICOLON, TokenType.EOF
        ]
        self.assertEqual(types, expected)
        self.assertEqual(tokens[0].value, "a")
        self.assertEqual(tokens[2].value, "10")

    def test_lexer_multiline(self):
        code = "a = 1;\nb = 2;\n"
        tokens = Lexer(code).tokenize()
        idents = [t.value for t in tokens if t.type == TokenType.IDENTIFIER]
        self.assertEqual(idents, ["a", "b"])

    def test_parser_produces_ast(self):
        code = "a = b + 5;"
        tokens = Lexer(code).tokenize()
        ast = Parser(tokens).parse()
        self.assertIsInstance(ast, ProgramNode)
        stmt = ast.statements[0]
        self.assertIsInstance(stmt, AssignNode)
        self.assertEqual(stmt.target, "a")
        self.assertIsInstance(stmt.expression, BinaryOpNode)
        self.assertEqual(stmt.expression.operator, "+")

    def test_parser_multiple_statements(self):
        code = "a = 1;\nb = a + 2;\nc = b;\n"
        ast = Parser(Lexer(code).tokenize()).parse()
        self.assertEqual(len(ast.statements), 3)


# ══════════════════════════════════════════════════════════
# 2. IR TESTS
# ══════════════════════════════════════════════════════════
class TestIR(unittest.TestCase):

    def test_tac_clone_independence(self):
        tac = compile_src("a = 5 + 3;\nb = a;")
        clone = tac.clone()
        # Mutating clone should not affect original
        clone.instructions[0].result = "MUTATED"
        self.assertNotEqual(tac.instructions[0].result, "MUTATED")

    def test_tac_size(self):
        tac = compile_src("a = 10 * 2;\nb = a + 0;\nc = b;")
        self.assertEqual(tac.size(), 5)

    def test_tac_dump_format(self):
        tac = compile_src("a = 1;")
        dump = tac.dump()
        self.assertIn("a =", dump)
        self.assertIn("0:", dump)


# ══════════════════════════════════════════════════════════
# 3. OPTIMIZATION PASS TESTS
# ══════════════════════════════════════════════════════════
class TestPasses(unittest.TestCase):

    def setUp(self):
        self.pipeline = OptiGuardPipeline()

    # --- Constant Folding ---
    def test_constant_folding_folds_binary(self):
        tac = compile_src("a = 10 * 2;")
        opt, modified = ConstantFoldingPass().run(tac)
        self.assertTrue(modified)
        vals = [i.arg1 for i in opt.instructions]
        self.assertIn(20, vals)

    def test_constant_folding_propagates(self):
        tac = compile_src("a = 5;\nb = a + 3;")
        opt, modified = ConstantFoldingPass().run(tac)
        self.assertTrue(modified)
        vals = [i.arg1 for i in opt.instructions]
        self.assertIn(8, vals)

    # --- Algebraic Simplification ---
    def test_alg_simp_add_zero(self):
        tac = compile_src("b = a + 0;")
        opt, modified = AlgebraicSimplificationPass().run(tac)
        self.assertTrue(modified)
        plus_ops = [i for i in opt.instructions if i.op == '+']
        self.assertEqual(len(plus_ops), 0)

    def test_alg_simp_mul_one(self):
        tac = compile_src("b = a * 1;")
        opt, modified = AlgebraicSimplificationPass().run(tac)
        self.assertTrue(modified)
        mul_ops = [i for i in opt.instructions if i.op == '*']
        self.assertEqual(len(mul_ops), 0)

    def test_alg_simp_mul_zero(self):
        tac = compile_src("b = a * 0;")
        opt, modified = AlgebraicSimplificationPass().run(tac)
        self.assertTrue(modified)

    # --- Dead Code Elimination ---
    def test_dce_removes_dead_temp(self):
        code = "t0 = 5 + 5;\na = 20;\n"
        tac = compile_src(code)
        opt, modified = DeadCodeEliminationPass().run(tac)
        self.assertTrue(modified)
        results = [i.result for i in opt.instructions]
        self.assertNotIn("t0", results)
        self.assertIn("a", results)

    # --- CSE ---
    def test_cse_eliminates_repeated_expr(self):
        tac = compile_src("a = x + y;\nb = x + y;\n")
        opt, modified = CSEPass().run(tac)
        self.assertTrue(modified)
        # The second x+y should be replaced by a copy
        binary_ops = [i for i in opt.instructions if i.is_binary()]
        # Should have fewer binary ops than original (2 → 1)
        self.assertLess(len(binary_ops), 2)

    # --- Strength Reduction ---
    def test_strength_reduction_mul2(self):
        tac = compile_src("r = val * 2;")
        opt, modified = StrengthReductionPass().run(tac)
        self.assertTrue(modified)
        # Should have replaced mul with add
        mul_ops = [i for i in opt.instructions if i.op == '*']
        add_ops = [i for i in opt.instructions if i.op == '+']
        # Less multiplications, more additions
        self.assertGreater(len(add_ops), 0)

    def test_strength_reduction_mul4(self):
        tac = compile_src("r = val * 4;")
        opt, modified = StrengthReductionPass().run(tac)
        self.assertTrue(modified)

    # --- Copy Propagation ---
    def test_copy_propagation_chain(self):
        tac = compile_src("a = src;\nb = a;\n")
        opt, modified = CopyPropagationPass().run(tac)
        self.assertTrue(modified)
        # b should now reference src directly, not a
        b_instrs = [i for i in opt.instructions if i.result == 'b']
        if b_instrs:
            self.assertEqual(b_instrs[0].arg1, 'src')


# ══════════════════════════════════════════════════════════
# 4. ROLLBACK ENGINE TESTS
# ══════════════════════════════════════════════════════════
class TestRollbackEngine(unittest.TestCase):

    def _make_tac(self, source: str) -> TACProgram:
        return compile_src(source)

    def test_snapshot_push_pop(self):
        tac = self._make_tac("a = 5 + 3;")
        stack = SnapshotStack()
        original_size = tac.size()
        stack.push(tac)
        self.assertEqual(stack.depth(), 1)
        restored = stack.pop()
        self.assertEqual(restored.size(), original_size)
        self.assertEqual(stack.depth(), 0)

    def test_snapshot_commit_discards(self):
        tac = self._make_tac("a = 1;")
        stack = SnapshotStack()
        stack.push(tac)
        stack.commit()
        self.assertEqual(stack.depth(), 0)

    def test_snapshot_pop_empty_raises(self):
        stack = SnapshotStack()
        with self.assertRaises(IndexError):
            stack.pop()

    def test_snapshot_independence(self):
        tac = self._make_tac("a = 5 + 3;")
        stack = SnapshotStack()
        stack.push(tac)
        # Mutate original
        tac.instructions[0].result = "CHANGED"
        restored = stack.pop()
        self.assertNotEqual(restored.instructions[0].result, "CHANGED")

    def test_degradation_detector_accepts_improvement(self):
        detector = DegradationDetector()
        before = IRMetrics(instruction_count=10, distinct_variables=5, temporary_count=3, estimated_cycle_cost=20)
        after  = IRMetrics(instruction_count=7,  distinct_variables=4, temporary_count=2, estimated_cycle_cost=14)
        report = detector.check(before, after)
        self.assertFalse(report.degraded)
        self.assertLess(report.delta_j, 0)

    def test_degradation_detector_flags_degradation(self):
        detector = DegradationDetector()
        before = IRMetrics(instruction_count=5, distinct_variables=3, temporary_count=1, estimated_cycle_cost=8)
        after  = IRMetrics(instruction_count=8, distinct_variables=5, temporary_count=3, estimated_cycle_cost=15)
        report = detector.check(before, after)
        self.assertTrue(report.degraded)
        self.assertGreaterEqual(report.delta_j, 0)

    def test_degradation_detector_no_change_is_degraded(self):
        detector = DegradationDetector()
        m = IRMetrics(instruction_count=5, distinct_variables=3, temporary_count=1, estimated_cycle_cost=8)
        report = detector.check(m, m)
        # delta_j == 0 → degraded (strict improvement required)
        self.assertTrue(report.degraded)


# ══════════════════════════════════════════════════════════
# 5. FEATURE PROFILER TESTS
# ══════════════════════════════════════════════════════════
class TestFeatureProfiler(unittest.TestCase):

    def test_profiler_empty_program(self):
        tac = TACProgram()
        fv = FeatureProfiler.profile(tac)
        self.assertEqual(fv.instruction_count, 0)

    def test_profiler_binary_op_detected(self):
        tac = compile_src("a = 5 + 3;")
        fv = FeatureProfiler.profile(tac)
        self.assertEqual(fv.has_binary_ops, 1)

    def test_profiler_repeated_expr_detected(self):
        tac = compile_src("a = x + y;\nb = x + y;")
        fv = FeatureProfiler.profile(tac)
        self.assertEqual(fv.has_repeated_expr, 1)

    def test_profiler_temp_density(self):
        tac = compile_src("a = 5 + 3;")
        fv = FeatureProfiler.profile(tac)
        # There should be some temp (t0) in a 2-instruction TAC
        self.assertGreater(fv.temp_density, 0.0)


# ══════════════════════════════════════════════════════════
# 6. ADAPTIVE SELECTOR TESTS
# ══════════════════════════════════════════════════════════
class TestAdaptiveSelector(unittest.TestCase):

    def _make_passes(self):
        return [
            ConstantFoldingPass(),
            AlgebraicSimplificationPass(),
            DeadCodeEliminationPass(),
            CSEPass(),
            StrengthReductionPass(),
            CopyPropagationPass(),
        ]

    def test_selector_returns_pass(self):
        from optiguard.profiler.feature_profiler import FeatureVector
        selector = AdaptivePassSelector(self._make_passes())
        fv = FeatureVector(instruction_count=5, has_binary_ops=1, constant_density=0.5)
        chosen = selector.select(fv)
        self.assertIsNotNone(chosen)

    def test_selector_respects_tabu(self):
        from optiguard.profiler.feature_profiler import FeatureVector
        passes = self._make_passes()
        selector = AdaptivePassSelector(passes)
        for p in passes:
            selector.add_to_tabu(p.name)
        fv = FeatureVector()
        chosen = selector.select(fv)
        self.assertIsNone(chosen)

    def test_selector_all_exhausted(self):
        passes = self._make_passes()
        selector = AdaptivePassSelector(passes)
        for p in passes:
            selector.add_to_tabu(p.name)
        self.assertTrue(selector.all_exhausted())


# ══════════════════════════════════════════════════════════
# 7. PIPELINE END-TO-END TESTS
# ══════════════════════════════════════════════════════════
class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = OptiGuardPipeline(use_adaptive=True)
        self.seq_pipeline = OptiGuardPipeline(use_adaptive=False)

    def test_e2e_canonical_spec(self):
        """The canonical project specification example must show improvement."""
        code = """
a = 10 * 2;
b = a + 0;
c = b;
"""
        result = self.pipeline.optimize(code)
        # At minimum, cycle cost must be reduced (the adaptive pipeline may reduce
        # instruction count, cycle cost, or both — either is a valid optimization)
        instr_improved = result.initial_metrics.instruction_count > result.final_metrics.instruction_count
        cycle_improved = result.initial_metrics.estimated_cycle_cost > result.final_metrics.estimated_cycle_cost
        self.assertTrue(
            instr_improved or cycle_improved,
            f"Expected at least instruction or cycle improvement. "
            f"Initial: {result.initial_metrics}, Final: {result.final_metrics}"
        )
        self.assertGreater(result.improvement_summary["cycle_reduction_pct"], 0.0)

    def test_e2e_sequential_mode_canonical(self):
        code = """
a = 10 * 2;
b = a + 0;
c = b;
"""
        result = self.seq_pipeline.optimize(code)
        self.assertGreater(
            result.initial_metrics.instruction_count,
            result.final_metrics.instruction_count
        )

    def test_e2e_rollback_count_in_result(self):
        code = "x = 10 + 5;\ny = x * 1;\nz = y + 0;\n"
        result = self.pipeline.optimize(code)
        # rollback_count should be non-negative integer
        self.assertGreaterEqual(result.rollback_count, 0)
        self.assertIsInstance(result.rollback_count, int)

    def test_e2e_converges(self):
        code = "a = 1;\nb = 2;\nc = a + b;\n"
        result = self.pipeline.optimize(code)
        # After full adaptive run, pipeline should converge
        self.assertTrue(result.converged)

    def test_e2e_steps_recorded(self):
        code = "a = 10 * 2;\nb = a + 0;\n"
        result = self.pipeline.optimize(code)
        self.assertGreater(len(result.steps), 0)
        for step in result.steps:
            self.assertIn(step.accepted, (True, False))

    def test_e2e_deep_constant_chain(self):
        code = """
a = 5;
b = a + 3;
c = b * 2;
d = c - 1;
e = d + 0;
f = e;
"""
        result = self.pipeline.optimize(code)
        self.assertLessEqual(
            result.final_metrics.instruction_count,
            result.initial_metrics.instruction_count
        )

    def test_e2e_strength_reduction_case(self):
        code = "r1 = val * 2;\nr2 = val * 4;\n"
        result = self.pipeline.optimize(code)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.final_tac)


# ══════════════════════════════════════════════════════════
# 8. BENCHMARK SUITE TEST
# ══════════════════════════════════════════════════════════
class TestBenchmarks(unittest.TestCase):

    def test_all_benchmarks_run_without_error(self):
        from benchmark.programs import BENCHMARK_PROGRAMS
        pipeline = OptiGuardPipeline(use_adaptive=True)
        for bm in BENCHMARK_PROGRAMS:
            with self.subTest(benchmark=bm["name"]):
                try:
                    result = pipeline.optimize(bm["source"])
                    self.assertIsNotNone(result.final_tac)
                    self.assertGreaterEqual(result.rollback_count, 0)
                except Exception as e:
                    self.fail(f"Benchmark '{bm['name']}' raised: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
