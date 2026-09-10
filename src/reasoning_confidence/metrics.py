from __future__ import annotations

import math
import re
import statistics
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateAgreement:
    paired_count: int
    comparable_count: int
    exact_agreement_count: int
    agreement_fraction: float | None


@dataclass(frozen=True)
class ConfidenceComparison:
    paired_value_count: int
    mean_absolute_difference: float | None
    median_absolute_difference: float | None
    maximum_absolute_difference: float | None
    pearson_correlation: float | None
    spearman_correlation: float | None


@dataclass(frozen=True)
class PrecisionComparison:
    candidate_agreement: CandidateAgreement
    confidence: ConfidenceComparison


@dataclass(frozen=True)
class ProbeTokenAccounting:
    released_probe_tokens: int
    boundary_probe_tokens: int
    avoided_probe_tokens: int
    reduction_fraction: float

    @property
    def reduction_percent(self) -> float:
        return 100.0 * self.reduction_fraction


def normalize_candidate(candidate: str | None) -> str | None:
    if candidate is None:
        return None
    normalized = unicodedata.normalize("NFC", candidate)
    return re.sub(r"\s+", " ", normalized).strip()


def candidate_agreement(
    left_candidates: Sequence[str | None], right_candidates: Sequence[str | None]
) -> CandidateAgreement:
    if len(left_candidates) != len(right_candidates):
        raise ValueError("candidate sequences must have equal length")
    comparable = 0
    agreement = 0
    for left, right in zip(left_candidates, right_candidates):
        normalized_left = normalize_candidate(left)
        normalized_right = normalize_candidate(right)
        if normalized_left is None or normalized_right is None:
            continue
        comparable += 1
        agreement += int(normalized_left == normalized_right)
    return CandidateAgreement(
        paired_count=len(left_candidates),
        comparable_count=comparable,
        exact_agreement_count=agreement,
        agreement_fraction=agreement / comparable if comparable else None,
    )


def _finite_pairs(
    left_values: Sequence[float | None], right_values: Sequence[float | None]
) -> tuple[tuple[float, float], ...]:
    if len(left_values) != len(right_values):
        raise ValueError("confidence sequences must have equal length")
    pairs: list[tuple[float, float]] = []
    for left, right in zip(left_values, right_values):
        if left is None or right is None:
            continue
        left_float = float(left)
        right_float = float(right)
        if not math.isfinite(left_float) or not math.isfinite(right_float):
            continue
        pairs.append((left_float, right_float))
    return tuple(pairs)


def _pearson(left_values: Sequence[float], right_values: Sequence[float]) -> float | None:
    if len(left_values) < 2:
        return None
    left_mean = statistics.fmean(left_values)
    right_mean = statistics.fmean(right_values)
    numerator = math.fsum(
        (left - left_mean) * (right - right_mean)
        for left, right in zip(left_values, right_values)
    )
    left_scale = math.sqrt(math.fsum((left - left_mean) ** 2 for left in left_values))
    right_scale = math.sqrt(math.fsum((right - right_mean) ** 2 for right in right_values))
    if left_scale == 0.0 or right_scale == 0.0:
        return None
    return numerator / (left_scale * right_scale)


def _average_ranks(values: Sequence[float]) -> tuple[float, ...]:
    ranked = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    start = 0
    while start < len(ranked):
        end = start + 1
        while end < len(ranked) and ranked[end][1] == ranked[start][1]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for index, _ in ranked[start:end]:
            result[index] = rank
        start = end
    return tuple(result)


def paired_confidence_comparison(
    left_values: Sequence[float | None], right_values: Sequence[float | None]
) -> ConfidenceComparison:
    pairs = _finite_pairs(left_values, right_values)
    if not pairs:
        return ConfidenceComparison(0, None, None, None, None, None)
    left = tuple(pair[0] for pair in pairs)
    right = tuple(pair[1] for pair in pairs)
    differences = tuple(abs(first - second) for first, second in pairs)
    return ConfidenceComparison(
        paired_value_count=len(pairs),
        mean_absolute_difference=statistics.fmean(differences),
        median_absolute_difference=statistics.median(differences),
        maximum_absolute_difference=max(differences),
        pearson_correlation=_pearson(left, right),
        spearman_correlation=_pearson(_average_ranks(left), _average_ranks(right)),
    )


def paired_precision_comparison(
    left_candidates: Sequence[str | None],
    right_candidates: Sequence[str | None],
    left_confidences: Sequence[float | None],
    right_confidences: Sequence[float | None],
) -> PrecisionComparison:
    return PrecisionComparison(
        candidate_agreement=candidate_agreement(left_candidates, right_candidates),
        confidence=paired_confidence_comparison(left_confidences, right_confidences),
    )


def probe_token_accounting(
    released_probe_tokens: int, boundary_probe_tokens: int
) -> ProbeTokenAccounting:
    released = int(released_probe_tokens)
    boundary = int(boundary_probe_tokens)
    if released <= 0:
        raise ValueError("released_probe_tokens must be positive")
    if boundary < 0 or boundary > released:
        raise ValueError("boundary_probe_tokens must be between zero and released tokens")
    avoided = released - boundary
    return ProbeTokenAccounting(
        released_probe_tokens=released,
        boundary_probe_tokens=boundary,
        avoided_probe_tokens=avoided,
        reduction_fraction=avoided / released,
    )
