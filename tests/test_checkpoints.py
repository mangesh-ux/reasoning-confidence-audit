import unittest

from reasoning_confidence.checkpoints import (
    find_released_style_checkpoints,
    prefix_before_checkpoint,
)


class CheckpointTests(unittest.TestCase):
    def test_individual_membership_matches_wait_ids_and_eos(self) -> None:
        response = [9, 42, 7, 43, 8]
        checkpoints = find_released_style_checkpoints(
            response,
            wait_token_ids=[42, 43],
            eos_token_id=7,
        )

        self.assertEqual([match.response_token_position for match in checkpoints], [1, 2, 3])
        self.assertEqual(
            [match.matched_membership for match in checkpoints],
            ["wait_token_membership", "eos_token", "wait_token_membership"],
        )

    def test_prefix_excludes_matched_checkpoint_token(self) -> None:
        response = [9, 42, 7]
        checkpoint = find_released_style_checkpoints(
            response,
            wait_token_ids=[42],
            eos_token_id=7,
        )[0]

        self.assertEqual(prefix_before_checkpoint(response, checkpoint), (9,))


if __name__ == "__main__":
    unittest.main()
