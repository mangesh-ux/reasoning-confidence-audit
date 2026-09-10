from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BoxBoundary:
    raw_text: str
    source: str
    opening_char_index: int | None
    closing_char_index: int | None
    marker_char_index: int | None
    reason: str | None

    @property
    def completed(self) -> bool:
        return (
            self.opening_char_index is not None
            and self.closing_char_index is not None
            and self.reason is None
        )

    @property
    def braced_candidate(self) -> str | None:
        if not self.completed:
            return None
        return self.raw_text[self.opening_char_index : self.closing_char_index + 1]

    @property
    def boxed_expression(self) -> str | None:
        candidate = self.braced_candidate
        if candidate is None:
            return None
        return "\\boxed" + candidate

    @property
    def boxed_body(self) -> str | None:
        candidate = self.braced_candidate
        if candidate is None:
            return None
        return candidate[1:-1]


@dataclass(frozen=True)
class CandidateTokenSpan:
    opening_token_index: int | None
    closing_token_index: int | None
    included_token_indices: tuple[int, ...]
    characters_after_close_in_closing_token: str | None
    reason: str | None

    @property
    def completed(self) -> bool:
        return self.opening_token_index is not None and self.closing_token_index is not None


def is_escaped(text: str, character_index: int) -> bool:
    slash_count = 0
    cursor = character_index - 1
    while cursor >= 0 and text[cursor] == "\\":
        slash_count += 1
        cursor -= 1
    return slash_count % 2 == 1


def structural_braces(
    text: str, *, escaped_braces_are_structural: bool = False
) -> tuple[tuple[int, str], ...]:
    return tuple(
        (index, character)
        for index, character in enumerate(text)
        if character in "{}"
        and (escaped_braces_are_structural or not is_escaped(text, index))
    )


def _boundary_from_opening(
    text: str,
    opening_char_index: int,
    *,
    source: str,
    marker_char_index: int | None,
    escaped_braces_are_structural: bool,
) -> BoxBoundary:
    if opening_char_index >= len(text) or text[opening_char_index] != "{":
        raise ValueError("opening_char_index must point to an opening brace")
    if is_escaped(text, opening_char_index) and not escaped_braces_are_structural:
        return BoxBoundary(
            raw_text=text,
            source=source,
            opening_char_index=None,
            closing_char_index=None,
            marker_char_index=marker_char_index,
            reason="outer_open_brace_is_escaped",
        )
    depth = 0
    for index, character in structural_braces(
        text, escaped_braces_are_structural=escaped_braces_are_structural
    ):
        if index < opening_char_index:
            continue
        if character == "{":
            depth += 1
            continue
        depth -= 1
        if depth == 0:
            return BoxBoundary(
                raw_text=text,
                source=source,
                opening_char_index=opening_char_index,
                closing_char_index=index,
                marker_char_index=marker_char_index,
                reason=None,
            )
        if depth < 0:
            return BoxBoundary(
                raw_text=text,
                source=source,
                opening_char_index=opening_char_index,
                closing_char_index=None,
                marker_char_index=marker_char_index,
                reason="outer_brace_depth_became_negative",
            )
    return BoxBoundary(
        raw_text=text,
        source=source,
        opening_char_index=opening_char_index,
        closing_char_index=None,
        marker_char_index=marker_char_index,
        reason="outer_box_not_closed",
    )


def find_first_boxed_boundary(text: str, *, start: int = 0) -> BoxBoundary:
    marker = "\\boxed"
    marker_char_index = text.find(marker, start)
    if marker_char_index < 0:
        return BoxBoundary(
            raw_text=text,
            source="boxed_expression",
            opening_char_index=None,
            closing_char_index=None,
            marker_char_index=None,
            reason="boxed_marker_not_found",
        )
    after_marker = marker_char_index + len(marker)
    opening_char_index = after_marker
    while opening_char_index < len(text) and text[opening_char_index].isspace():
        opening_char_index += 1
    if opening_char_index >= len(text):
        return BoxBoundary(
            raw_text=text,
            source="boxed_expression",
            opening_char_index=None,
            closing_char_index=None,
            marker_char_index=marker_char_index,
            reason="missing_outer_open_brace",
        )
    if text[opening_char_index] != "{":
        return BoxBoundary(
            raw_text=text,
            source="boxed_expression",
            opening_char_index=None,
            closing_char_index=None,
            marker_char_index=marker_char_index,
            reason="unexpected_text_before_outer_open_brace",
        )
    return _boundary_from_opening(
        text,
        opening_char_index,
        source="boxed_expression",
        marker_char_index=marker_char_index,
        escaped_braces_are_structural=False,
    )


def find_forced_candidate_boundary(generated_text: str) -> BoxBoundary:
    if not generated_text:
        return BoxBoundary(
            raw_text=generated_text,
            source="forced_suffix",
            opening_char_index=None,
            closing_char_index=None,
            marker_char_index=None,
            reason="awaiting_outer_open_brace",
        )
    if generated_text[0] != "{":
        return BoxBoundary(
            raw_text=generated_text,
            source="forced_suffix",
            opening_char_index=None,
            closing_char_index=None,
            marker_char_index=None,
            reason="first_generated_character_is_not_outer_open_brace",
        )
    return _boundary_from_opening(
        generated_text,
        0,
        source="forced_suffix",
        marker_char_index=None,
        escaped_braces_are_structural=True,
    )


def _token_index_for_character(
    token_pieces: Sequence[str], character_index: int
) -> tuple[int, int, int]:
    cursor = 0
    for token_index, piece in enumerate(token_pieces):
        next_cursor = cursor + len(piece)
        if cursor <= character_index < next_cursor:
            return token_index, cursor, next_cursor
        cursor = next_cursor
    raise ValueError("boundary character does not belong to a token piece")


def candidate_token_span(
    token_pieces: Sequence[str], boundary: BoxBoundary
) -> CandidateTokenSpan:
    combined_text = "".join(token_pieces)
    if combined_text != boundary.raw_text:
        raise ValueError("token pieces do not reconstruct the boundary text")
    if not boundary.completed:
        return CandidateTokenSpan(
            opening_token_index=None,
            closing_token_index=None,
            included_token_indices=(),
            characters_after_close_in_closing_token=None,
            reason=boundary.reason,
        )
    opening_token_index, _, _ = _token_index_for_character(
        token_pieces, boundary.opening_char_index
    )
    closing_token_index, closing_start, closing_end = _token_index_for_character(
        token_pieces, boundary.closing_char_index
    )
    included = tuple(range(opening_token_index + 1, closing_token_index))
    after_close_start = boundary.closing_char_index + 1
    characters_after_close = combined_text[after_close_start:closing_end]
    reason = None if included else "no_complete_candidate_payload_token"
    return CandidateTokenSpan(
        opening_token_index=opening_token_index,
        closing_token_index=closing_token_index,
        included_token_indices=included,
        characters_after_close_in_closing_token=characters_after_close,
        reason=reason,
    )
