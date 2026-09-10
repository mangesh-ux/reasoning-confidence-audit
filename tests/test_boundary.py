import unittest

from reasoning_confidence.boundary import (
    candidate_token_span,
    find_first_boxed_boundary,
    find_forced_candidate_boundary,
)


class BoundaryTests(unittest.TestCase):
    def test_simple_forced_box_has_q7_token_span(self) -> None:
        pieces = ["{", "42", "}"]
        boundary = find_forced_candidate_boundary("".join(pieces))
        span = candidate_token_span(pieces, boundary)

        self.assertTrue(boundary.completed)
        self.assertEqual(boundary.boxed_expression, "\\boxed{42}")
        self.assertEqual(boundary.boxed_body, "42")
        self.assertEqual(span.opening_token_index, 0)
        self.assertEqual(span.closing_token_index, 2)
        self.assertEqual(span.included_token_indices, (1,))

    def test_nested_text_construct_closes_at_matching_outer_brace(self) -> None:
        text = r"\boxed{\text{a{b}}} trailing"
        boundary = find_first_boxed_boundary(text)

        self.assertTrue(boundary.completed)
        self.assertEqual(boundary.boxed_expression, r"\boxed{\text{a{b}}}")
        self.assertEqual(boundary.boxed_body, r"\text{a{b}}")

    def test_incomplete_forced_box_is_not_a_candidate(self) -> None:
        boundary = find_forced_candidate_boundary(r"{\text{unfinished}")
        span = candidate_token_span([r"{\text", "{", "unfinished", "}"], boundary)

        self.assertFalse(boundary.completed)
        self.assertEqual(boundary.reason, "outer_box_not_closed")
        self.assertEqual(span.included_token_indices, ())
        self.assertIsNone(boundary.boxed_expression)

    def test_span_records_characters_after_close_in_closing_token(self) -> None:
        pieces = ["{", "x", "}post"]
        boundary = find_forced_candidate_boundary("".join(pieces))
        span = candidate_token_span(pieces, boundary)

        self.assertTrue(span.completed)
        self.assertEqual(span.included_token_indices, (1,))
        self.assertEqual(span.characters_after_close_in_closing_token, "post")

    def test_escaped_braces_are_ignored_for_offline_boxed_parser(self) -> None:
        boundary = find_first_boxed_boundary(r"\boxed{\{x\}}")

        self.assertTrue(boundary.completed)
        self.assertEqual(boundary.boxed_body, r"\{x\}")


if __name__ == "__main__":
    unittest.main()
