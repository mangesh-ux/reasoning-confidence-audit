from __future__ import annotations

import math
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reasoning_confidence.boundary import candidate_token_span, find_forced_candidate_boundary
from reasoning_confidence.confidence import boundary_aligned_confidence, released_full_span_confidence
from reasoning_confidence.metrics import probe_token_accounting


def main() -> None:
    token_pieces = ["{", "42", "}", " continued", " text"]
    chosen_logprobs = [-0.1, -0.2, -0.3, -0.4, -0.5]
    boundary = find_forced_candidate_boundary("".join(token_pieces))
    span = candidate_token_span(token_pieces, boundary)
    released = released_full_span_confidence(chosen_logprobs)
    bac = boundary_aligned_confidence(
        chosen_logprobs,
        opening_token_index=span.opening_token_index,
        closing_token_index=span.closing_token_index,
    )
    accounting = probe_token_accounting(len(token_pieces), span.closing_token_index + 1)

    print(f"candidate: {boundary.boxed_expression}")
    print(f"released full-span confidence: {released:.6f}")
    print(f"boundary-aligned confidence: {bac:.6f}")
    print(f"released probe tokens: {accounting.released_probe_tokens}")
    print(f"boundary-stopped probe tokens: {accounting.boundary_probe_tokens}")
    print(f"probe-token reduction: {100.0 * accounting.reduction_fraction:.2f}%")
    print(f"BAC check: {math.isclose(bac, math.exp(-0.2))}")


if __name__ == "__main__":
    main()
