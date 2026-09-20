"""Deterministic reference-based evaluation for mathematical answers.

This is pre-inference scaffolding only.  It makes no model, dataset, network,
or file-system requests.  ``math-verify`` is used when installed; an absent
backend, malformed input, empty parse, and backend exception remain distinct
outcomes rather than becoming an incorrect label.

``EvaluationResult`` intentionally contains no raw reference or candidate
text.  Callers that retain those private inputs must do so under their own
data-governance rules.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from importlib.metadata import PackageNotFoundError, version as package_version
from typing import Protocol, Sequence


EVALUATOR_IMPLEMENTATION_VERSION = "0.1.0"
"""Version of this evaluator contract, to record in a future frozen manifest."""


class EvaluationStatus(str, Enum):
    """Terminal states emitted by :func:`evaluate_answer`."""

    EVALUATED = "evaluated"
    NOT_EVALUABLE_MISSING_REFERENCE = "not_evaluable_missing_reference"
    NOT_EVALUABLE_MISSING_CANDIDATE = "not_evaluable_missing_candidate"
    NOT_EVALUABLE_EMPTY_REFERENCE = "not_evaluable_empty_reference"
    NOT_EVALUABLE_EMPTY_CANDIDATE = "not_evaluable_empty_candidate"
    NOT_EVALUABLE_MALFORMED_REFERENCE = "not_evaluable_malformed_reference"
    NOT_EVALUABLE_MALFORMED_CANDIDATE = "not_evaluable_malformed_candidate"
    NOT_EVALUABLE_EMPTY_REFERENCE_PARSE = "not_evaluable_empty_reference_parse"
    NOT_EVALUABLE_EMPTY_CANDIDATE_PARSE = "not_evaluable_empty_candidate_parse"
    NOT_EVALUABLE_BACKEND_UNAVAILABLE = "not_evaluable_backend_unavailable"
    ERROR_INVALID_REFERENCE_TYPE = "error_invalid_reference_type"
    ERROR_INVALID_CANDIDATE_TYPE = "error_invalid_candidate_type"
    ERROR_REFERENCE_PARSE = "error_reference_parse"
    ERROR_CANDIDATE_PARSE = "error_candidate_parse"
    ERROR_UNEXPECTED_REFERENCE_PARSE_RESULT = "error_unexpected_reference_parse_result"
    ERROR_UNEXPECTED_CANDIDATE_PARSE_RESULT = "error_unexpected_candidate_parse_result"
    ERROR_VERIFY = "error_verify"
    ERROR_UNEXPECTED_VERIFY_RESULT = "error_unexpected_verify_result"


class EvaluationBackend(Protocol):
    """Small adapter contract for a deterministic symbolic evaluator."""

    name: str
    version: str | None

    def parse(self, text: str) -> Sequence[object]:
        """Return parsed candidate objects, or raise a backend exception."""

    def verify(
        self, reference: Sequence[object], candidate: Sequence[object]
    ) -> bool:
        """Return an exact boolean equivalence result, or raise an exception."""


@dataclass(frozen=True)
class EvaluationResult:
    """Public-safe result of one reference/candidate comparison.

    ``correct`` is populated only for ``evaluated`` outcomes.  In particular,
    an error or non-evaluable condition is never represented as ``False``.
    """

    status: EvaluationStatus
    correct: bool | None
    backend_name: str | None
    backend_version: str | None
    parsed_reference_count: int | None = None
    parsed_candidate_count: int | None = None
    error_kind: str | None = None

    def __post_init__(self) -> None:
        if self.status is EvaluationStatus.EVALUATED:
            if type(self.correct) is not bool:
                raise ValueError("evaluated results require an exact boolean correctness value")
        elif self.correct is not None:
            raise ValueError("non-evaluated results must not carry a correctness label")

    @property
    def evaluable(self) -> bool:
        """Whether a symbolic comparison completed successfully."""

        return self.status is EvaluationStatus.EVALUATED


@dataclass(frozen=True)
class _MathVerifyBackend:
    """Adapter that fixes the call surface used from ``math-verify``."""

    parse_function: Callable[..., Sequence[object]]
    verify_function: Callable[..., bool]
    version: str | None
    name: str = "math-verify"

    def parse(self, text: str) -> Sequence[object]:
        # ``None`` delegates timeout enforcement to the future process-level
        # execution boundary, avoiding a host-dependent hidden timeout here.
        return self.parse_function(
            text,
            parsing_timeout=None,
            raise_on_error=True,
        )

    def verify(
        self, reference: Sequence[object], candidate: Sequence[object]
    ) -> bool:
        return self.verify_function(
            reference,
            candidate,
            timeout_seconds=None,
            raise_on_error=True,
        )


_MATH_VERIFY_IMPORT_ERROR_KIND: str | None = None
try:
    from math_verify import parse as _math_verify_parse
    from math_verify import verify as _math_verify_verify
except Exception as error:  # Optional dependency: preserve unavailable state at runtime.
    _math_verify_parse = None
    _math_verify_verify = None
    _MATH_VERIFY_IMPORT_ERROR_KIND = type(error).__name__


def _installed_math_verify_version() -> str | None:
    try:
        return package_version("math-verify")
    except PackageNotFoundError:
        return None


_DEFAULT_BACKEND: EvaluationBackend | None
if _math_verify_parse is None or _math_verify_verify is None:
    _DEFAULT_BACKEND = None
else:
    _DEFAULT_BACKEND = _MathVerifyBackend(
        parse_function=_math_verify_parse,
        verify_function=_math_verify_verify,
        version=_installed_math_verify_version(),
    )

_USE_DEFAULT_BACKEND = object()
_BOXED_MARKER = r"\boxed"


def evaluator_provenance() -> dict[str, object]:
    """Return public-safe evaluator/backend metadata for manifest recording.

    The version is observed rather than silently assumed.  A future study must
    freeze this returned information before benchmark inference begins.
    """

    return {
        "implementation": "activation_continuation.answer_evaluation",
        "implementation_version": EVALUATOR_IMPLEMENTATION_VERSION,
        "backend_name": _DEFAULT_BACKEND.name if _DEFAULT_BACKEND else "math-verify",
        "backend_version": _DEFAULT_BACKEND.version if _DEFAULT_BACKEND else None,
        "backend_available": _DEFAULT_BACKEND is not None,
        "backend_import_error_kind": _MATH_VERIFY_IMPORT_ERROR_KIND,
        "parse_options": {"parsing_timeout": None, "raise_on_error": True},
        "verify_options": {"timeout_seconds": None, "raise_on_error": True},
        "boxed_syntax_policy": "reject_unbalanced_outer_boxed_v1",
    }


def evaluate_answer(
    reference: str | None,
    candidate: str | None,
    *,
    backend: EvaluationBackend | None | object = _USE_DEFAULT_BACKEND,
) -> EvaluationResult:
    """Compare one candidate with one reference using a deterministic backend.

    Passing ``backend=None`` is useful for testing the unavailable-backend
    outcome.  Normal callers should omit it and record
    :func:`evaluator_provenance` before using the evaluator on study data.
    """

    selected_backend = (
        _DEFAULT_BACKEND if backend is _USE_DEFAULT_BACKEND else backend
    )
    backend_name, backend_version = _backend_identity(selected_backend)

    input_result = _validate_inputs(reference, candidate, backend_name, backend_version)
    if input_result is not None:
        return input_result

    # The type/None checks above narrow these values without converting them.
    assert isinstance(reference, str)
    assert isinstance(candidate, str)

    malformed_status = _malformed_boxed_status(reference, candidate)
    if malformed_status is not None:
        return EvaluationResult(
            status=malformed_status,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
        )

    if selected_backend is None:
        return EvaluationResult(
            status=EvaluationStatus.NOT_EVALUABLE_BACKEND_UNAVAILABLE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            error_kind=_MATH_VERIFY_IMPORT_ERROR_KIND,
        )

    try:
        parsed_reference = selected_backend.parse(reference)
    except Exception as error:
        return EvaluationResult(
            status=EvaluationStatus.ERROR_REFERENCE_PARSE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            error_kind=type(error).__name__,
        )
    reference_count = _parsed_count(parsed_reference)
    if reference_count is None:
        return EvaluationResult(
            status=EvaluationStatus.ERROR_UNEXPECTED_REFERENCE_PARSE_RESULT,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
        )
    if reference_count == 0:
        return EvaluationResult(
            status=EvaluationStatus.NOT_EVALUABLE_EMPTY_REFERENCE_PARSE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            parsed_reference_count=reference_count,
        )

    try:
        parsed_candidate = selected_backend.parse(candidate)
    except Exception as error:
        return EvaluationResult(
            status=EvaluationStatus.ERROR_CANDIDATE_PARSE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            parsed_reference_count=reference_count,
            error_kind=type(error).__name__,
        )
    candidate_count = _parsed_count(parsed_candidate)
    if candidate_count is None:
        return EvaluationResult(
            status=EvaluationStatus.ERROR_UNEXPECTED_CANDIDATE_PARSE_RESULT,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            parsed_reference_count=reference_count,
        )
    if candidate_count == 0:
        return EvaluationResult(
            status=EvaluationStatus.NOT_EVALUABLE_EMPTY_CANDIDATE_PARSE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            parsed_reference_count=reference_count,
            parsed_candidate_count=candidate_count,
        )

    try:
        verified = selected_backend.verify(parsed_reference, parsed_candidate)
    except Exception as error:
        return EvaluationResult(
            status=EvaluationStatus.ERROR_VERIFY,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            parsed_reference_count=reference_count,
            parsed_candidate_count=candidate_count,
            error_kind=type(error).__name__,
        )
    if type(verified) is not bool:
        return EvaluationResult(
            status=EvaluationStatus.ERROR_UNEXPECTED_VERIFY_RESULT,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            parsed_reference_count=reference_count,
            parsed_candidate_count=candidate_count,
        )

    return EvaluationResult(
        status=EvaluationStatus.EVALUATED,
        correct=verified,
        backend_name=backend_name,
        backend_version=backend_version,
        parsed_reference_count=reference_count,
        parsed_candidate_count=candidate_count,
    )


def _backend_identity(
    backend: EvaluationBackend | None | object,
) -> tuple[str | None, str | None]:
    if backend is None:
        return "math-verify", None
    if backend is _USE_DEFAULT_BACKEND:
        return "math-verify", None
    return (
        getattr(backend, "name", type(backend).__name__),
        getattr(backend, "version", None),
    )


def _validate_inputs(
    reference: str | None,
    candidate: str | None,
    backend_name: str | None,
    backend_version: str | None,
) -> EvaluationResult | None:
    if reference is None:
        return EvaluationResult(
            status=EvaluationStatus.NOT_EVALUABLE_MISSING_REFERENCE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
        )
    if candidate is None:
        return EvaluationResult(
            status=EvaluationStatus.NOT_EVALUABLE_MISSING_CANDIDATE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
        )
    if not isinstance(reference, str):
        return EvaluationResult(
            status=EvaluationStatus.ERROR_INVALID_REFERENCE_TYPE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            error_kind=type(reference).__name__,
        )
    if not isinstance(candidate, str):
        return EvaluationResult(
            status=EvaluationStatus.ERROR_INVALID_CANDIDATE_TYPE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
            error_kind=type(candidate).__name__,
        )
    if not reference.strip():
        return EvaluationResult(
            status=EvaluationStatus.NOT_EVALUABLE_EMPTY_REFERENCE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
        )
    if not candidate.strip():
        return EvaluationResult(
            status=EvaluationStatus.NOT_EVALUABLE_EMPTY_CANDIDATE,
            correct=None,
            backend_name=backend_name,
            backend_version=backend_version,
        )
    return None


def _malformed_boxed_status(
    reference: str, candidate: str
) -> EvaluationStatus | None:
    if _has_malformed_boxed_expression(reference):
        return EvaluationStatus.NOT_EVALUABLE_MALFORMED_REFERENCE
    if _has_malformed_boxed_expression(candidate):
        return EvaluationStatus.NOT_EVALUABLE_MALFORMED_CANDIDATE
    return None


def _has_malformed_boxed_expression(text: str) -> bool:
    """Conservatively reject an unclosed ``\\boxed{...}`` expression.

    This structural check occurs before symbolic parsing because permissive
    parsers can sometimes recover a partial expression from malformed LaTeX.
    It does not rewrite or extract an answer; balanced text is passed through
    unchanged to the pinned backend.
    """

    search_start = 0
    while True:
        marker_index = text.find(_BOXED_MARKER, search_start)
        if marker_index < 0:
            return False
        open_index = marker_index + len(_BOXED_MARKER)
        if open_index < len(text) and text[open_index].isalpha():
            # This is a longer command whose name merely begins with ``boxed``.
            search_start = open_index
            continue
        while open_index < len(text) and text[open_index].isspace():
            open_index += 1
        if open_index == len(text) or text[open_index] != "{":
            return True
        close_index = _matching_unescaped_brace(text, open_index)
        if close_index is None:
            return True
        search_start = close_index + 1


def _matching_unescaped_brace(text: str, open_index: int) -> int | None:
    """Find the close matching ``open_index`` while retaining escaped braces."""

    depth = 1
    for index in range(open_index + 1, len(text)):
        character = text[index]
        if character not in "{}" or _is_escaped(text, index):
            continue
        if character == "{":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return index
    return None


def _is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def _parsed_count(parsed: object) -> int | None:
    try:
        count = len(parsed)  # type: ignore[arg-type]
    except TypeError:
        return None
    return count if isinstance(count, int) and count >= 0 else None
