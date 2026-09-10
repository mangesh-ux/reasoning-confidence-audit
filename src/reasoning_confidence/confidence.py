from __future__ import annotations

import math
from collections.abc import Sequence


def _validated_logprobs(chosen_logprobs: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in chosen_logprobs)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("chosen log probabilities must be finite")
    return values


def geometric_mean_from_logprobs(chosen_logprobs: Sequence[float]) -> float:
    values = _validated_logprobs(chosen_logprobs)
    if not values:
        raise ValueError("at least one chosen log probability is required")
    return math.exp(math.fsum(values) / len(values))


def released_full_span_confidence(chosen_logprobs: Sequence[float]) -> float:
    values = _validated_logprobs(chosen_logprobs)
    if len(values) < 3:
        raise ValueError("released full-span reconstruction requires a nonempty window")
    return math.exp(math.fsum(values[1:-1]) / (len(values) - 1))


def boundary_aligned_confidence(
    chosen_logprobs: Sequence[float],
    *,
    opening_token_index: int,
    closing_token_index: int,
) -> float:
    values = _validated_logprobs(chosen_logprobs)
    if opening_token_index < 0 or closing_token_index >= len(values):
        raise IndexError("boundary token indexes must be inside the generated sequence")
    if closing_token_index <= opening_token_index + 1:
        raise ValueError("BAC requires at least one token between outer braces")
    return geometric_mean_from_logprobs(values[opening_token_index + 1 : closing_token_index])


def bac_from_included_logprobs(chosen_logprobs: Sequence[float]) -> float:
    return geometric_mean_from_logprobs(chosen_logprobs)
