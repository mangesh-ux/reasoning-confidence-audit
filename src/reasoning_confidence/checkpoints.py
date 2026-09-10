from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True)
class CheckpointMatch:
    checkpoint_index: int
    response_token_position: int
    matched_token_id: int
    matched_membership: str


def released_checkpoint_membership(
    wait_token_ids: Sequence[int], eos_token_id: int | None
) -> frozenset[int]:
    membership = {int(token_id) for token_id in wait_token_ids}
    if eos_token_id is not None:
        membership.add(int(eos_token_id))
    if not membership:
        raise ValueError("at least one released-style checkpoint token ID is required")
    return frozenset(membership)


def find_released_style_checkpoints(
    response_token_ids: Sequence[int],
    *,
    wait_token_ids: Sequence[int],
    eos_token_id: int | None,
) -> tuple[CheckpointMatch, ...]:
    wait_membership = frozenset(int(token_id) for token_id in wait_token_ids)
    membership = released_checkpoint_membership(wait_token_ids, eos_token_id)
    matches: list[CheckpointMatch] = []
    for response_token_position, raw_token_id in enumerate(response_token_ids):
        token_id = int(raw_token_id)
        if token_id not in membership:
            continue
        if token_id in wait_membership:
            matched_membership = "wait_token_membership"
        else:
            matched_membership = "eos_token"
        matches.append(
            CheckpointMatch(
                checkpoint_index=len(matches),
                response_token_position=response_token_position,
                matched_token_id=token_id,
                matched_membership=matched_membership,
            )
        )
    return tuple(matches)


def prefix_before_checkpoint(
    response_token_ids: Sequence[int], checkpoint: CheckpointMatch
) -> tuple[int, ...]:
    if checkpoint.response_token_position < 0:
        raise ValueError("checkpoint position must be non-negative")
    if checkpoint.response_token_position >= len(response_token_ids):
        raise IndexError("checkpoint position is outside the response token sequence")
    return tuple(int(token_id) for token_id in response_token_ids[: checkpoint.response_token_position])
