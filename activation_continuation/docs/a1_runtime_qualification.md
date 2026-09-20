# A1 — Runtime Qualification

**Qualification date:** 2026-09-14
**Status:** **TERMINAL — COMPUTE INFEASIBLE IN THE CURRENT EXECUTION ENVIRONMENT**

## Decision

The authorized primary runtime is native Transformers with
`Qwen/Qwen3-1.7B` in BF16 thinking mode, followed by a 4,096-generated-token
synthetic qualification before any benchmark call. That qualification could
not start because the operating system blocks GPU access and the pinned Torch
environment has no CUDA device.

Tier A, B, and C therefore remain unselected. Tier C cannot be shown to be
reliably completable in this environment, so the study stops at the
pre-benchmark compute gate. This is an infrastructure result, not a result
about activation signals, continuation value, Qwen3, MATH, or GSM8K.

No benchmark data were downloaded, loaded, selected, or passed to a model. No
target-model weights were downloaded or loaded. No base trajectory,
checkpoint, forced-answer probe, hidden activation, train/validation output,
or test output exists for this study.

## Frozen intended runtime

| Item | Intended value | Status |
| --- | --- | --- |
| Model | `Qwen/Qwen3-1.7B`, native Transformers, BF16 | Not loaded |
| Thinking template | `enable_thinking=True` | Not exercised |
| Candidate base decoding | temperature 0.6, top-p 0.95, top-k 20, min-p 0 | Not exercised |
| Maximum reasoning generation | 4,096 tokens | Not exercised |
| Qualification prompts | Hand-authored synthetic, non-benchmark prompts only | Not exercised |
| Benchmark source rows | MATH-family / GSM8K | **0 rows accessed** |

The official model card lists 28 layers, a 32,768-token context, BF16 weights,
and recommends the stated thinking-mode sampling settings; it also warns not
to use greedy decoding in thinking mode. See
[Qwen/Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B).

## Live preflight evidence

The following read-only GPU command was run under an elevated execution
context on 2026-09-14:

```text
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
```

Its complete result was:

```text
Failed to initialize NVML: GPU access blocked by the operating system
```

The existing isolated Python environment was then inspected without loading a
model or executing generation. Its relevant result was:

```text
torch: 2.9.1+cu128
transformers: 4.51.3
cuda_build: 12.8
cuda_available: false
bf16_supported: false
```

Torch also emitted a CUDA device-count initialization error. This independently
agrees with the NVML failure; the qualification did not treat an old hardware
manifest as evidence that a currently inaccessible GPU is usable.

The requested model is not already cached locally. Free disk space was about
98 GB at preflight, so storage is not the observed blocker. The blocker is
the absence of an accessible CUDA device required to establish reliable BF16
generation, hidden-state extraction, peak-VRAM behavior, and recovery.

## Required qualification checks

| Requirement | Outcome | Reason |
| --- | --- | --- |
| BF16 model fits reliably | Not evaluable | No CUDA device is accessible. |
| Repeated synthetic generation | Not run | A model could not be safely initialized on the required runtime. |
| Hidden-state extraction | Not run | Requires the unavailable target-model execution path. |
| 4,096-token context/generation safety | Not run | Requires synthetic generation. |
| Progressive-memory-leak check | Not run | Requires repeated GPU cycles. |
| Restart/resume behavior | Code-level testable only; no runtime evidence | No model request could be issued. |
| Activation serialization | Code-level testable only; no runtime evidence | No activation can be extracted. |
| Evaluator behavior | Isolated fixture tests may run; not a runtime pass | It cannot establish end-to-end model qualification. |
| Tokens/sec, wall time, peak VRAM, disk estimate | Not estimable | No target-model generation is possible. |

Zero synthetic cycles are recorded rather than replaced with CPU runs or a
different model. CPU execution would not qualify the predeclared native-BF16
GPU design and would not repair the unavailable GPU path.

## Tier decision and terminal consequence

| Tier | Required unique problems / trajectories | Decision |
| --- | --- | --- |
| A | 900 / at least 1,800 | Not eligible for selection |
| B | 600 / at least 1,200 | Not eligible for selection |
| C | 400 / at least 800 | **Compute infeasible in this environment** |

The protocol explicitly prohibits falling back to a tiny study when Tier C
cannot be completed reliably. No smaller study, alternate precision, alternate
model, altered generation cap, CPU substitute, or historical artifact reuse
was attempted.

## Resumption condition

This program may be reconsidered only after an external environment change
restores usable CUDA access. A future run must perform a fresh, extended,
synthetic non-benchmark qualification from the new environment; it may not
claim this report as a successful qualification, reuse an unmeasured tier, or
silently modify the study design. Because no benchmark inference began, no
study manifest was created or frozen.
