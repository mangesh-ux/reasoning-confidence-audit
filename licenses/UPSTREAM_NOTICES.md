# Upstream notices

This public release does not redistribute the upstream CoDE-Stop repository,
llama.cpp source or binaries, benchmark datasets, Qwen model weights, raw
reasoning trajectories, raw token-logprob traces, or code from the papers
listed below.

## CoDE-Stop

The audit concerns
[sudoparsa/CoDE-Stop](https://github.com/sudoparsa/CoDE-Stop) at commit
`b5081e7c2abe23bb1d19649421cc13522fee7c50`. The checked upstream repository
declares the MIT License, copyright (c) 2026 Parsa Hosseini. If upstream source
is obtained or redistributed, retain its complete upstream license and notices.

The upstream paper is *Early Stopping for Large Reasoning Models via Confidence
Dynamics*, Parsa Hosseini, Sumit Nawathe, Mahdi Salmani, Meisam Razaviyayn, and
Soheil Feizi (2026), [arXiv:2604.04930](https://arxiv.org/abs/2604.04930).

## llama.cpp

The recorded inference runtime is
[ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) at commit
`7798007a29a90e3053e799394da48cf53a2f8e0f`. llama.cpp declares the MIT
License, copyright (c) 2023–2026 the ggml authors. No llama.cpp material is
bundled here.

## Model and completed-study data

The recorded model source is
[Qwen/Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B), revision
`1cfa9a7208912126459214e8b04321603b3df60c`. No weights or converted GGUFs
are included. Use the model card and associated terms before obtaining or
using the model.

The completed audit records provenance for `HuggingFaceH4/aime_2024` and
`opencompass/AIME2025`; no dataset rows are redistributed. The unrun next-study
protocol names MATH500 but does not include it. Obtain every dataset from its
source and comply with the applicable terms.

## Related work cited as references only

[Conformal Thinking](https://arxiv.org/abs/2602.03814),
[PUMA / Stop When Reasoning Converges](https://arxiv.org/abs/2605.17672), and
[*From token probabilities to calibrated confidence*](https://arxiv.org/abs/2608.07827)
are cited as related work only. Their source code, paper text, model assets,
and data are not bundled. The preliminary Conformal Thinking repository is not
vendored; any future use must respect its then-current license and terms.
