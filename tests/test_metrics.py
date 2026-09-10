import unittest

from reasoning_confidence.metrics import (
    candidate_agreement,
    paired_confidence_comparison,
    probe_token_accounting,
)


class MetricTests(unittest.TestCase):
    def test_candidate_agreement_ignores_unavailable_pairs(self) -> None:
        result = candidate_agreement(
            ["\\boxed{2}", None, "\\boxed{x}"],
            ["  \\boxed{2}  ", "\\boxed{3}", "\\boxed{y}"],
        )

        self.assertEqual(result.paired_count, 3)
        self.assertEqual(result.comparable_count, 2)
        self.assertEqual(result.exact_agreement_count, 1)
        self.assertAlmostEqual(result.agreement_fraction, 0.5)

    def test_paired_confidence_comparison_uses_finite_pairs_only(self) -> None:
        result = paired_confidence_comparison([0.2, None, 0.8], [0.3, 0.5, 0.6])

        self.assertEqual(result.paired_value_count, 2)
        self.assertAlmostEqual(result.mean_absolute_difference, 0.15)
        self.assertAlmostEqual(result.maximum_absolute_difference, 0.2)

    def test_probe_token_accounting_matches_holdout_formula(self) -> None:
        accounting = probe_token_accounting(756, 156)

        self.assertEqual(accounting.avoided_probe_tokens, 600)
        self.assertAlmostEqual(accounting.reduction_fraction, 600 / 756)
        self.assertAlmostEqual(accounting.reduction_percent, 79.36507936507937)


if __name__ == "__main__":
    unittest.main()
