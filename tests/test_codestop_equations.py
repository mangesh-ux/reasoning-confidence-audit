import math
import unittest

from reasoning_confidence.codestop_equations import (
    RELEASED_TRIAL_MAX_SELECTED_TOKENS,
    degeneration_score,
    inclusive_ungated_stop_instrument,
    one_based_ramp_interpretation,
    released_default_degeneration_score,
    released_ramp_threshold,
    released_stop_decision,
    released_terminal_membership,
    released_trial_cap_reached,
    released_trial_score,
    temporal_weight,
)


class CoDEStopEquationTests(unittest.TestCase):
    def test_released_geometric_score_preserves_exclusions_and_denominator(self) -> None:
        value = released_trial_score((0.9, 0.8, 0.7, 0.6), ewt=True)

        self.assertAlmostEqual(value, math.exp((math.log(0.8) + math.log(0.7)) / 3.0))

    def test_released_arithmetic_score_preserves_exclusions_and_denominator(self) -> None:
        value = released_trial_score((0.9, 0.8, 0.7, 0.6), ewt=False)

        self.assertAlmostEqual(value, (0.8 + 0.7) / 3.0)

    def test_two_token_score_reconstructs_released_edge(self) -> None:
        self.assertEqual(released_trial_score((0.9, 0.8), ewt=True), 1.0)
        self.assertEqual(released_trial_score((0.9, 0.8), ewt=False), 0.0)

    def test_one_token_score_is_preserved_as_undefined(self) -> None:
        with self.assertRaises(ValueError):
            released_trial_score((0.9,), ewt=True)

    def test_released_cap_is_twenty_one_selected_tokens(self) -> None:
        self.assertEqual(RELEASED_TRIAL_MAX_SELECTED_TOKENS, 21)
        self.assertFalse(released_trial_cap_reached(20))
        self.assertTrue(released_trial_cap_reached(21))

    def test_terminal_completion_is_token_id_membership(self) -> None:
        terminal_ids = (101, 102, 999)

        self.assertTrue(released_terminal_membership(101, terminal_ids))
        self.assertTrue(released_terminal_membership(999, terminal_ids))
        self.assertFalse(released_terminal_membership(103, terminal_ids))

    def test_default_log_score_is_weighted_strict_drop_count_on_fixture(self) -> None:
        score = released_default_degeneration_score((10, 20, 30), (0.9, 0.8, 0.7))

        self.assertAlmostEqual(score, math.log(1.5) + 2.0)

    def test_raw_domain_with_released_drop_gate_diverges_from_default(self) -> None:
        score = degeneration_score(
            (10, 20, 30),
            (0.9, 0.8, 0.7),
            log_domain=False,
            require_strict_drop=True,
            apply_released_warmup=True,
        )

        self.assertEqual(score, 0.0)

    def test_log_domain_no_gate_diagnostic_matches_drop_fixture(self) -> None:
        score = degeneration_score(
            (10, 20, 30),
            (0.9, 0.8, 0.7),
            log_domain=True,
            require_strict_drop=False,
            apply_released_warmup=True,
        )

        self.assertAlmostEqual(score, math.log(1.5) + 2.0)

    def test_log_floor_collapses_tiny_raw_decreases(self) -> None:
        # Post-freeze source-fidelity regression: not an L1 comparison outcome.
        score = released_default_degeneration_score(
            (10, 20, 30),
            (1e-13, 1e-14, 1e-15),
        )

        self.assertEqual(score, 0.0)

    def test_raw_ungated_indicator_includes_small_improvements(self) -> None:
        score = degeneration_score(
            (10, 20, 30),
            (0.4, 0.45, 0.46),
            log_domain=False,
            require_strict_drop=False,
            apply_released_warmup=True,
        )

        self.assertAlmostEqual(score, math.log(1.5) + 2.0)

    def test_strict_drop_gate_excludes_small_improvements(self) -> None:
        score = degeneration_score(
            (10, 20, 30),
            (0.4, 0.45, 0.46),
            log_domain=False,
            require_strict_drop=True,
            apply_released_warmup=True,
        )

        self.assertEqual(score, 0.0)

    def test_strict_drop_gate_excludes_equal_confidences(self) -> None:
        ungated = degeneration_score(
            (10, 20, 30),
            (0.4, 0.4, 0.4),
            log_domain=False,
            require_strict_drop=False,
            apply_released_warmup=True,
        )
        gated = degeneration_score(
            (10, 20, 30),
            (0.4, 0.4, 0.4),
            log_domain=False,
            require_strict_drop=True,
            apply_released_warmup=True,
        )

        self.assertAlmostEqual(ungated, math.log(1.5) + 2.0)
        self.assertEqual(gated, 0.0)

    def test_method_warmup_overrides_two_check_helper_value(self) -> None:
        score = released_default_degeneration_score((10, 20), (0.9, 0.8))

        self.assertEqual(score, 0.0)

    def test_weight_recomputes_against_current_horizon(self) -> None:
        self.assertAlmostEqual(temporal_weight(30, 20), math.log(30 / 20) + 1.0)
        self.assertAlmostEqual(temporal_weight(60, 20), math.log(60 / 20) + 1.0)
        self.assertGreater(temporal_weight(60, 20), temporal_weight(30, 20))

    def test_zero_based_and_one_based_ramps_differ_at_early_checks(self) -> None:
        released = tuple(
            released_ramp_threshold(index, 2, 0.90, 0.95) for index in range(3)
        )
        one_based = tuple(
            one_based_ramp_interpretation(number, 2, 0.90, 0.95)
            for number in range(1, 4)
        )

        self.assertEqual(released, (0.90, 0.925, 0.95))
        self.assertEqual(one_based, (0.925, 0.95, 0.95))

    def test_strict_confidence_equality_does_not_stop_but_inclusive_does(self) -> None:
        released = released_stop_decision(
            0.90,
            0.90,
            0.10,
            0.20,
            confidence_requires_terminal_eligibility=True,
            terminal_eligible=True,
        )
        inclusive = inclusive_ungated_stop_instrument(0.90, 0.90, 0.10, 0.20)

        self.assertFalse(released)
        self.assertTrue(inclusive)

    def test_strict_degeneration_equality_does_not_stop_but_inclusive_does(self) -> None:
        released = released_stop_decision(
            0.10,
            0.20,
            0.50,
            0.50,
            confidence_requires_terminal_eligibility=True,
            terminal_eligible=True,
        )
        inclusive = inclusive_ungated_stop_instrument(0.10, 0.20, 0.50, 0.50)

        self.assertFalse(released)
        self.assertTrue(inclusive)

    def test_terminal_gate_only_suppresses_confidence_branch(self) -> None:
        gated_confidence = released_stop_decision(
            0.91,
            0.90,
            0.10,
            0.20,
            confidence_requires_terminal_eligibility=True,
            terminal_eligible=False,
        )
        ungated_confidence = released_stop_decision(
            0.91,
            0.90,
            0.10,
            0.20,
            confidence_requires_terminal_eligibility=False,
            terminal_eligible=False,
        )
        degeneration_stop = released_stop_decision(
            0.10,
            0.90,
            0.21,
            0.20,
            confidence_requires_terminal_eligibility=True,
            terminal_eligible=False,
        )

        self.assertFalse(gated_confidence)
        self.assertTrue(ungated_confidence)
        self.assertTrue(degeneration_stop)


if __name__ == "__main__":
    unittest.main()
