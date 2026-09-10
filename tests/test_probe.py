import math
import unittest

from reasoning_confidence.probe import CompletionChoice, run_boundary_probe


class FakeCompletionClient:
    def __init__(self) -> None:
        self.choices = iter(
            [
                CompletionChoice(token_id=1, text="{", logprob=-0.1),
                CompletionChoice(token_id=2, text="42", logprob=-0.2),
                CompletionChoice(token_id=3, text="}", logprob=-0.3),
                CompletionChoice(token_id=4, text="should-not-run", logprob=-0.4),
            ]
        )
        self.inputs: list[tuple[int, ...]] = []

    def complete_one(self, input_token_ids: list[int] | tuple[int, ...]) -> CompletionChoice:
        self.inputs.append(tuple(input_token_ids))
        return next(self.choices)


class ProbeTests(unittest.TestCase):
    def test_probe_stops_at_outer_close_without_continuation(self) -> None:
        client = FakeCompletionClient()

        result = run_boundary_probe(
            client,
            base_prompt_token_ids=[10],
            reasoning_prefix_token_ids=[20, 21],
            final_answer_suffix_token_ids=[30],
            max_candidate_tokens=8,
        )

        self.assertEqual(result.termination_reason, "outer_box_closed")
        self.assertEqual(len(result.tokens), 3)
        self.assertEqual(len(client.inputs), 3)
        self.assertEqual(client.inputs[0], (10, 20, 21, 30))
        self.assertEqual(result.candidate_expression, "\\boxed{42}")
        self.assertAlmostEqual(result.bac, math.exp(-0.2))


if __name__ == "__main__":
    unittest.main()
