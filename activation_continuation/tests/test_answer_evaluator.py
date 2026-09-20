"""Synthetic unit tests for the deterministic answer-evaluation contract."""

from __future__ import annotations

import unittest

from activation_continuation.answer_evaluation import (
    EvaluationResult,
    EvaluationStatus,
    evaluate_answer,
    evaluator_provenance,
)


class _ExplodingBackend:
    """Synthetic backend used to ensure exceptions never become false labels."""

    name = "synthetic-exploding-backend"
    version = "fixture"

    def parse(self, text: str) -> list[object]:
        raise RuntimeError("synthetic parse failure")

    def verify(self, reference: list[object], candidate: list[object]) -> bool:
        raise AssertionError("verify must not run after a parse failure")


MATH_VERIFY_AVAILABLE = bool(evaluator_provenance()["backend_available"])


@unittest.skipUnless(MATH_VERIFY_AVAILABLE, "math-verify is not installed")
class MathVerifyFixtureTests(unittest.TestCase):
    """Required pre-inference fixtures using only hand-written literals."""

    def assert_correct(self, reference: str, candidate: str) -> EvaluationResult:
        result = evaluate_answer(reference, candidate)
        self.assertEqual(result.status, EvaluationStatus.EVALUATED)
        self.assertTrue(result.evaluable)
        self.assertIs(result.correct, True)
        self.assertEqual(result.backend_name, "math-verify")
        self.assertGreater(result.parsed_reference_count or 0, 0)
        self.assertGreater(result.parsed_candidate_count or 0, 0)
        return result

    def test_integer_answer(self) -> None:
        self.assert_correct("42", r"\boxed{42}")

    def test_decimal_answer(self) -> None:
        self.assert_correct("0.125", r"\boxed{0.125}")

    def test_signed_answer(self) -> None:
        self.assert_correct("-7", r"\boxed{-7}")

    def test_fraction_answer(self) -> None:
        self.assert_correct(r"\boxed{\frac{1}{2}}", r"\boxed{\frac{2}{4}}")

    def test_algebraically_equivalent_expressions(self) -> None:
        self.assert_correct(
            r"\boxed{x^2 + 2x + 1}",
            r"\boxed{(x+1)^2}",
        )

    def test_latex_boxed_answer(self) -> None:
        self.assert_correct(r"\boxed{\sqrt{2}}", r"\boxed{\sqrt{2}}")

    def test_percentage_answer(self) -> None:
        self.assert_correct(r"\boxed{25\%}", "0.25")

    def test_gsm8k_delimiter_formatting(self) -> None:
        self.assert_correct(
            "A calculation gives 42.\n#### 42",
            "Working omitted.\n#### 42",
        )

    def test_actual_wrong_answer_is_evaluated_false(self) -> None:
        result = evaluate_answer("2", r"\boxed{3}")
        self.assertEqual(result.status, EvaluationStatus.EVALUATED)
        self.assertIs(result.correct, False)
        self.assertTrue(result.evaluable)

    def test_malformed_box_is_not_evaluable(self) -> None:
        result = evaluate_answer("2", r"\boxed{\frac{1}{2}")
        self.assertEqual(result.status, EvaluationStatus.NOT_EVALUABLE_MALFORMED_CANDIDATE)
        self.assertIsNone(result.correct)
        self.assertFalse(result.evaluable)
        self.assertIsNone(result.parsed_candidate_count)

    def test_empty_candidate_is_not_evaluable(self) -> None:
        result = evaluate_answer("2", " \t\n ")
        self.assertEqual(result.status, EvaluationStatus.NOT_EVALUABLE_EMPTY_CANDIDATE)
        self.assertIsNone(result.correct)
        self.assertFalse(result.evaluable)

    def test_empty_symbolic_parse_is_not_evaluable(self) -> None:
        result = evaluate_answer("2", r"\boxed{}")
        self.assertEqual(result.status, EvaluationStatus.NOT_EVALUABLE_EMPTY_CANDIDATE_PARSE)
        self.assertIsNone(result.correct)
        self.assertEqual(result.parsed_candidate_count, 0)


class EvaluatorStateTests(unittest.TestCase):
    """State-machine tests independent of the optional symbolic package."""

    def test_explicit_unavailable_backend_is_not_a_false_label(self) -> None:
        result = evaluate_answer("2", "2", backend=None)
        self.assertEqual(result.status, EvaluationStatus.NOT_EVALUABLE_BACKEND_UNAVAILABLE)
        self.assertIsNone(result.correct)
        self.assertFalse(result.evaluable)

    def test_backend_parse_exception_is_preserved_as_an_error(self) -> None:
        result = evaluate_answer("2", "2", backend=_ExplodingBackend())
        self.assertEqual(result.status, EvaluationStatus.ERROR_REFERENCE_PARSE)
        self.assertIsNone(result.correct)
        self.assertEqual(result.error_kind, "RuntimeError")

    def test_non_string_candidate_is_not_coerced(self) -> None:
        result = evaluate_answer("2", 2)  # type: ignore[arg-type]
        self.assertEqual(result.status, EvaluationStatus.ERROR_INVALID_CANDIDATE_TYPE)
        self.assertIsNone(result.correct)
        self.assertEqual(result.error_kind, "int")

    def test_result_does_not_retain_raw_answer_fields(self) -> None:
        result = evaluate_answer("2", "2", backend=None)
        self.assertNotIn("reference", result.__dict__)
        self.assertNotIn("candidate", result.__dict__)


if __name__ == "__main__":
    unittest.main()
