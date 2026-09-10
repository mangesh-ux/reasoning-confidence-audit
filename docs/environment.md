# Environment and provenance

## Completed audit runtime

| Item | Recorded value or role |
| --- | --- |
| Base model | `Qwen/Qwen3-4B` |
| Model revision | `1cfa9a7208912126459214e8b04321603b3df60c` |
| llama.cpp revision | `7798007a29a90e3053e799394da48cf53a2f8e0f` |
| CoDE-Stop revision | `b5081e7c2abe23bb1d19649421cc13522fee7c50` |
| Q4_K_M SHA-256 | `069872af6a408c4d3998f6ecd15b0028ac3b38839be6dd98f80a84493e9c0a20` |
| Q8_0 SHA-256 | `0d5964f2837d157bf8d845f09b006254b85389ef4293ec0f41dd8ffeab1ab3f0` |
| BF16 anchor SHA-256 | `89ee1fd110158671b341bf4a8d45bd4859f60ac1ef7252e89233d2492f712814` |

Q4_K_M is retained as the historical exploratory/discovery backend. Q8_0 is
the primary practical validation backend because Q7’s frozen-prefix probes
tracked BF16 candidate identity more closely. BF16 is a limited fidelity anchor
because local execution may offload heavily and was intentionally restricted to
a predefined subset.

Q7 verified that the pinned quantizer supported Q8_0 and TQ1_0 generation.
TQ1_0 did not have usable CUDA inference support in the pinned source and was
used only as a CPU-only extreme post-training ternary stress condition.

## Public aggregate check

The compact result packager requires only a recent Python interpreter with the
standard library. No model, GPU, server, or dataset access is needed for the
public verification command in the repository README.

The public `reasoning_confidence` package, its synthetic unit tests, and its
synthetic example also require only the Python standard library. Its optional
completion client can contact a separately started local llama.cpp server, but
it neither starts nor configures that runtime.

## Full reproduction boundary

A full inference rerun requires separately obtaining the upstream CoDE-Stop
repository, llama.cpp, the Qwen model, and benchmark data under their own
licenses and terms. It also requires preserving the pinned revisions and
recording local binary hashes, tokenizer behavior, prompt template, GPU/CPU
placement, drivers, context size, and decoding settings. None of those assets
are redistributed here.
