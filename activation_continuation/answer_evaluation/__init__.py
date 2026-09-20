"""Deterministic, reference-based answer-evaluation scaffolding.

The public API deliberately reports non-evaluable and backend-error outcomes
separately from evaluated incorrect answers.
"""

from .evaluator import (
    EVALUATOR_IMPLEMENTATION_VERSION,
    EvaluationBackend,
    EvaluationResult,
    EvaluationStatus,
    evaluate_answer,
    evaluator_provenance,
)

__all__ = [
    "EVALUATOR_IMPLEMENTATION_VERSION",
    "EvaluationBackend",
    "EvaluationResult",
    "EvaluationStatus",
    "evaluate_answer",
    "evaluator_provenance",
]
