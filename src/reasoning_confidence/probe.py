from __future__ import annotations

import json
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.request import Request, urlopen

from .boundary import BoxBoundary, CandidateTokenSpan, candidate_token_span, find_forced_candidate_boundary
from .confidence import boundary_aligned_confidence


class CompletionResponseError(RuntimeError):
    pass


@dataclass(frozen=True)
class GreedyCompletionConfig:
    base_url: str
    timeout_seconds: float = 30.0
    seed: int = 42
    n_probs: int = 5
    cache_prompt: bool = True

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise ValueError("base_url is required")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.n_probs < 0:
            raise ValueError("n_probs must be non-negative")


@dataclass(frozen=True)
class CompletionChoice:
    token_id: int
    text: str
    logprob: float


@dataclass(frozen=True)
class ProbeToken:
    token_index: int
    token_id: int
    text: str
    logprob: float


@dataclass(frozen=True)
class BoundaryProbeResult:
    termination_reason: str
    tokens: tuple[ProbeToken, ...]
    boundary: BoxBoundary
    token_span: CandidateTokenSpan
    bac: float | None
    wall_seconds: float

    @property
    def candidate_expression(self) -> str | None:
        return self.boundary.boxed_expression


class OneTokenCompletionClient(Protocol):
    def complete_one(self, input_token_ids: Sequence[int]) -> CompletionChoice:
        ...


class LlamaCompletionClient:
    def __init__(self, config: GreedyCompletionConfig) -> None:
        self.config = config

    def _payload(self, input_token_ids: Sequence[int]) -> dict[str, Any]:
        return {
            "prompt": [int(token_id) for token_id in input_token_ids],
            "n_predict": 1,
            "temperature": 0.0,
            "top_p": 1.0,
            "top_k": 0,
            "min_p": 0.0,
            "typical_p": 1.0,
            "repeat_penalty": 1.0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "dry_multiplier": 0.0,
            "xtc_probability": 0.0,
            "seed": self.config.seed,
            "n_probs": self.config.n_probs,
            "post_sampling_probs": False,
            "return_tokens": True,
            "timings_per_token": True,
            "cache_prompt": self.config.cache_prompt,
            "stream": False,
        }

    def complete_one(self, input_token_ids: Sequence[int]) -> CompletionChoice:
        body = json.dumps(self._payload(input_token_ids), ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.config.base_url.rstrip('/')}/completion",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.config.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return completion_choice_from_response(payload)


def completion_choice_from_response(payload: Mapping[str, Any]) -> CompletionChoice:
    response_tokens = payload.get("tokens")
    probabilities = payload.get("completion_probabilities")
    if not isinstance(response_tokens, list) or not isinstance(probabilities, list):
        raise CompletionResponseError("response lacks token or probability arrays")
    if len(response_tokens) != 1 or len(probabilities) != 1:
        raise CompletionResponseError("one-token probing requires exactly one token and probability")
    entry = probabilities[0]
    if not isinstance(entry, Mapping):
        raise CompletionResponseError("probability entry must be an object")
    token_id = int(response_tokens[0])
    if token_id != int(entry.get("id")):
        raise CompletionResponseError("selected token ID differs from probability-entry ID")
    try:
        logprob = float(entry["logprob"])
    except (KeyError, TypeError, ValueError) as error:
        raise CompletionResponseError("probability entry lacks a valid logprob") from error
    if not math.isfinite(logprob):
        raise CompletionResponseError("chosen logprob must be finite")
    text = _choice_text(payload, entry)
    return CompletionChoice(token_id=token_id, text=text, logprob=logprob)


def _choice_text(payload: Mapping[str, Any], entry: Mapping[str, Any]) -> str:
    raw_bytes = entry.get("bytes")
    if isinstance(raw_bytes, list):
        try:
            return bytes(int(value) for value in raw_bytes).decode("utf-8")
        except (TypeError, ValueError, UnicodeDecodeError):
            pass
    content = payload.get("content", "")
    return str(content)


def run_boundary_probe(
    client: OneTokenCompletionClient,
    *,
    base_prompt_token_ids: Sequence[int],
    reasoning_prefix_token_ids: Sequence[int],
    final_answer_suffix_token_ids: Sequence[int],
    max_candidate_tokens: int,
) -> BoundaryProbeResult:
    if max_candidate_tokens <= 0:
        raise ValueError("max_candidate_tokens must be positive")
    fixed_prompt_ids = tuple(
        int(token_id)
        for token_id in (
            tuple(base_prompt_token_ids)
            + tuple(reasoning_prefix_token_ids)
            + tuple(final_answer_suffix_token_ids)
        )
    )
    selected_ids: list[int] = []
    tokens: list[ProbeToken] = []
    pieces: list[str] = []
    boundary = find_forced_candidate_boundary("")
    started = time.perf_counter()
    termination_reason = f"no_outer_box_close_candidate_cap_{max_candidate_tokens}"
    for token_index in range(max_candidate_tokens):
        choice = client.complete_one(fixed_prompt_ids + tuple(selected_ids))
        selected_ids.append(choice.token_id)
        token = ProbeToken(
            token_index=token_index,
            token_id=choice.token_id,
            text=choice.text,
            logprob=choice.logprob,
        )
        tokens.append(token)
        pieces.append(choice.text)
        boundary = find_forced_candidate_boundary("".join(pieces))
        if boundary.completed:
            termination_reason = "outer_box_closed"
            break
        if boundary.reason == "first_generated_character_is_not_outer_open_brace":
            termination_reason = f"malformed_outer_box_{boundary.reason}"
            break
    token_span = candidate_token_span([token.text for token in tokens], boundary)
    bac = None
    if token_span.completed and token_span.included_token_indices:
        bac = boundary_aligned_confidence(
            [token.logprob for token in tokens],
            opening_token_index=token_span.opening_token_index,
            closing_token_index=token_span.closing_token_index,
        )
    return BoundaryProbeResult(
        termination_reason=termination_reason,
        tokens=tuple(tokens),
        boundary=boundary,
        token_span=token_span,
        bac=bac,
        wall_seconds=time.perf_counter() - started,
    )
