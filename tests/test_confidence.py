import math
import unittest

from reasoning_confidence.confidence import (
    boundary_aligned_confidence,
    released_full_span_confidence,
)


class ConfidenceTests(unittest.TestCase):
    def test_bac_uses_only_tokens_between_outer_braces(self) -> None:
        logprobs = [-0.1, -0.2, -0.3, -0.4]

        value = boundary_aligned_confidence(
            logprobs,
            opening_token_index=0,
            closing_token_index=2,
        )

        self.assertAlmostEqual(value, math.exp(-0.2))

    def test_released_full_span_uses_audit_denominator(self) -> None:
        logprobs = [-0.1, -0.2, -0.3, -0.4, -0.5]

        value = released_full_span_confidence(logprobs)

        self.assertAlmostEqual(value, math.exp((-0.2 - 0.3 - 0.4) / 4.0))

    def test_rejects_nonfinite_logprob(self) -> None:
        with self.assertRaises(ValueError):
            boundary_aligned_confidence(
                [-0.1, float("nan"), -0.3],
                opening_token_index=0,
                closing_token_index=2,
            )

    def test_bac_requires_a_payload_token(self) -> None:
        with self.assertRaises(ValueError):
            boundary_aligned_confidence(
                [-0.1, -0.2],
                opening_token_index=0,
                closing_token_index=1,
            )


if __name__ == "__main__":
    unittest.main()
