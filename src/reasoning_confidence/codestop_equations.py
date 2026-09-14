"""Pure, version-pinned arithmetic for the L1 CoDE-Stop semantics audit.

This module is deliberately not an upstream CoDE-Stop implementation.  It
contains no model, tokenizer, checkpoint-selection, or decoding code.  Its
functions reconstruct only the small numerical and Boolean expressions pinned
in ``docs/l1_equation_to_execution_protocol.md`` so that their distinctions can
be checked with synthetic inputs.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


RELEASED_DEGENERATION_DELTA = 0.55
RELEASED_LOG_FLOOR = 1e-12
RELEASED_TRIAL_MAX_SELECTED_TOKENS = 21


def _finite(value: float, *, name: str) -> float:
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite")
    return converted


def _probabilities(values: Sequence[float]) -> tuple[float, ...]:
    converted = tuple(_finite(value, name="probability") for value in values)
    if any(value <= 0.0 or value > 1.0 for value in converted):
        raise ValueError("probabilities must lie in (0, 1]")
    return converted


def _offsets(values: Sequence[int | float]) -> tuple[float, ...]:
    converted = tuple(_finite(value, name="token offset") for value in values)
    if any(value <= 0.0 for value in converted):
        raise ValueError("token offsets must be positive")
    if any(current <= previous for previous, current in zip(converted, converted[1:])):
        raise ValueError("token offsets must be strictly increasing")
    return converted


def released_trial_score(
    selected_token_probabilities: Sequence[float], *, ewt: bool
) -> float:
    """Reconstruct the released normal-path forced-answer score.

    The pinned helper excludes the first and final selected token but keeps an
    ``n - 1`` denominator.  ``ewt=True`` selects its geometric-like branch;
    ``ewt=False`` selects its arithmetic-like branch.  The helper's one-token
    expression has a zero denominator, so this reconstruction rejects it
    rather than inventing a repair.
    """

    probabilities = _probabilities(selected_token_probabilities)
    if len(probabilities) < 2:
        raise ValueError("released trial score is undefined for fewer than two tokens")
    denominator = len(probabilities) - 1
    included = probabilities[1:-1]
    if ewt:
        return math.exp(math.fsum(math.log(value) for value in included) / denominator)
    return math.fsum(included) / denominator


def released_trial_cap_reached(selected_token_count: int) -> bool:
    """Whether the helper's ``total_steps > 20`` cap has become true."""

    count = int(selected_token_count)
    if count < 0:
        raise ValueError("selected token count must be non-negative")
    return count >= RELEASED_TRIAL_MAX_SELECTED_TOKENS


def released_terminal_membership(
    last_token_id: int, terminal_token_ids: Sequence[int]
) -> bool:
    """Reconstruct terminal completion as final-token ID membership.

    This intentionally does not decode a string or require a complete
    multi-token delimiter sequence, matching the membership rule in the pinned
    helper.
    """

    membership = frozenset(int(token_id) for token_id in terminal_token_ids)
    if not membership:
        raise ValueError("at least one terminal token ID is required")
    return int(last_token_id) in membership


def temporal_weight(current_offset: int | float, checkpoint_offset: int | float) -> float:
    """Return the released Eq. 4 weight for one checkpoint offset."""

    current = _finite(current_offset, name="current token offset")
    checkpoint = _finite(checkpoint_offset, name="checkpoint token offset")
    if checkpoint <= 0.0 or current <= 0.0:
        raise ValueError("token offsets must be positive")
    if checkpoint > current:
        raise ValueError("checkpoint offset cannot exceed current offset")
    return math.log(current / checkpoint) + 1.0


def degeneration_score(
    token_offsets: Sequence[int | float],
    confidences: Sequence[float],
    *,
    log_domain: bool,
    require_strict_drop: bool,
    apply_released_warmup: bool,
) -> float:
    """Evaluate a predeclared degeneration-expression comparison instrument.

    ``log_domain=True`` uses the released ``log(max(c, 1e-12))`` transform.
    ``require_strict_drop=True`` adds the released outer filter.  The caller of
    the pinned helper replaces the score with zero until a third confidence
    check exists; ``apply_released_warmup`` captures that separate behavior.
    These switches are for source-audit fixtures only, not method search.
    """

    offsets = _offsets(token_offsets)
    probabilities = _probabilities(confidences)
    if len(offsets) != len(probabilities):
        raise ValueError("token offsets and confidences must have equal length")
    if apply_released_warmup and len(probabilities) < 3:
        return 0.0
    if len(probabilities) < 2:
        return 0.0

    values = (
        tuple(math.log(max(value, RELEASED_LOG_FLOOR)) for value in probabilities)
        if log_domain
        else probabilities
    )
    current_offset = offsets[-1]
    score = 0.0
    for _previous_offset, offset, previous, current in zip(
        offsets,
        offsets[1:],
        values,
        values[1:],
    ):
        if require_strict_drop and not previous > current:
            continue
        if 2.0 * current - previous < RELEASED_DEGENERATION_DELTA:
            score += temporal_weight(current_offset, offset)
    return score


def released_default_degeneration_score(
    token_offsets: Sequence[int | float], confidences: Sequence[float]
) -> float:
    """Reconstruct the released default degeneration path at method level."""

    return degeneration_score(
        token_offsets,
        confidences,
        log_domain=True,
        require_strict_drop=True,
        apply_released_warmup=True,
    )


def released_ramp_threshold(
    step_index: int, ramp_steps: int, ramp_min: float, ramp_max: float
) -> float:
    """Reconstruct the released zero-based confidence-ramp calculation."""

    index = int(step_index)
    steps = int(ramp_steps)
    if index < 0:
        raise ValueError("step index must be non-negative")
    lower = _finite(ramp_min, name="ramp minimum")
    upper = _finite(ramp_max, name="ramp maximum")
    alpha = min(1.0, index / steps) if steps > 0 else 1.0
    return lower + (upper - lower) * alpha


def one_based_ramp_interpretation(
    checkpoint_number: int, ramp_steps: int, ramp_min: float, ramp_max: float
) -> float:
    """Evaluate Eq. 2 when the first checkpoint is assigned coordinate one.

    This is a comparison instrument, not a claim that the paper mandates this
    coordinate convention.
    """

    number = int(checkpoint_number)
    if number < 1:
        raise ValueError("one-based checkpoint number must be at least one")
    return released_ramp_threshold(number, ramp_steps, ramp_min, ramp_max)


def released_stop_decision(
    confidence: float,
    effective_confidence_threshold: float,
    degeneration: float,
    degeneration_threshold: float,
    *,
    confidence_requires_terminal_eligibility: bool,
    terminal_eligible: bool,
) -> bool:
    """Reconstruct the released strict Boolean stop expression.

    The terminal eligibility flag is exposed independently so this audit does
    not toggle ``ewt`` itself, which also changes upstream score aggregation
    and terminal-token construction.
    """

    confidence_value = _finite(confidence, name="confidence")
    confidence_threshold = _finite(
        effective_confidence_threshold, name="effective confidence threshold"
    )
    degeneration_value = _finite(degeneration, name="degeneration score")
    degeneration_limit = _finite(
        degeneration_threshold, name="degeneration threshold"
    )
    confidence_stop = (
        (not confidence_requires_terminal_eligibility or terminal_eligible)
        and confidence_value > confidence_threshold
    )
    return confidence_stop or degeneration_value > degeneration_limit


def inclusive_ungated_stop_instrument(
    confidence: float,
    effective_confidence_threshold: float,
    degeneration: float,
    degeneration_threshold: float,
) -> bool:
    """Evaluate the inclusive, ungated comparison predicate for L1 only."""

    return (
        _finite(confidence, name="confidence")
        >= _finite(effective_confidence_threshold, name="effective confidence threshold")
    ) or (
        _finite(degeneration, name="degeneration score")
        >= _finite(degeneration_threshold, name="degeneration threshold")
    )
