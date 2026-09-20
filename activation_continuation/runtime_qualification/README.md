# Synthetic Runtime Qualification Harness

This private, isolated harness qualifies only hand-written synthetic prompts.
It is not a benchmark runner, does not read dataset rows, and does not produce
scientific model results. Its safe default is a dry run that freezes or checks
the plan and records CUDA availability without loading a model.

The native runner is `NativeTransformersBf16Qwen3Runner`. It uses native
Transformers `AutoTokenizer` and `AutoModelForCausalLM`, requests BF16 on
CUDA, uses a Qwen3 chat template with the frozen thinking-mode setting, and
sets `local_files_only=True` unconditionally. A missing local snapshot is a
qualification failure; it never triggers a download.

## Safety and resume contract

`RuntimeQualificationHarness.run()` is dry-run-only unless the caller passes
`execute_synthetic=True`. Even with explicit execution, CUDA must be available
before the runner can load a model. The fixed plan uses a 4,096-token maximum
generation design and at least two cycles per hand-written synthetic case.

The output directory contains:

- `qualification_plan.json`: created once with exclusive creation and checked
  byte-for-byte on resume;
- `qualification_ledger.jsonl`: append-only event evidence;
- `activations/<intent>/layer-*.acrq`: private float16 last-prefix activation
  vectors with a JSON header and SHA-256 recorded in the ledger.

Every planned synthetic cycle has a stable case/cycle/seed intent ID. The
synthetic runner sets both `min_new_tokens` and `max_new_tokens` to the frozen
4,096-token ceiling, so each completed cycle actually exercises the declared
long-generation path rather than merely accepting a maximum token setting.
Completed cycles are skipped on resume. Failed cycles are retained and skipped. A cycle
with a declaration or start record but no terminal record is
`interrupted_unknown`, so it is also never retried automatically: rerunning it
could silently replace an attempt that may already have reached the model.
Unstarted fixed intents can still proceed. This is intent determinism, not a
claim that sampled model text is bitwise deterministic across hardware.

## Intended A1 runtime-qualification fields

This file is a field schema, not an A1 result. The terminal A1 decision record
should state each field as observed, unavailable, failed, or not evaluated;
it must not turn a missing measurement into a pass.

| A1 field | Harness evidence | Required interpretation boundary |
| --- | --- | --- |
| Qualification identity | Plan fingerprint, run ID, source commit recorded by caller | Identify the exact isolated qualification only. |
| Synthetic-only scope | Frozen hand-written `SyntheticCase` IDs and prompt construction | State that no selected benchmark problem, benchmark output, or historical frozen artifact was used. |
| Model/runtime provenance | Requested model/tokenizer revisions, native Transformers/Torch/CUDA versions, device, BF16, local-only flag | Preserve exact values from `model_load_completed`; a failed or blocked load is not a model-fit pass. |
| CUDA availability | `cuda_detection` ledger event | Include Torch availability, CUDA availability, device count/name, runtime version, and diagnostic reason. |
| BF16 model-fit evidence | `model_load_started`, `model_load_completed` or `model_load_failed`, plus post-load memory snapshot | Do not infer fit when CUDA/model load was blocked or failed. |
| Repeated synthetic generation | One `intent_completed` record per fixed synthetic cycle | Report completed, failed, and interrupted-unknown counts without replacement. |
| Prefix activation extraction | Activation artifact headers, checksums, layer indexes, dimensions, source/stored dtype | This checks only the synthetic pre-generation extraction path, not a benchmark activation result. |
| 4,096-token context design | Per-cycle prompt length, configured required generation length, model context limit, safety flag | `context_limit_unavailable` is not evidence that the design is safe. |
| Throughput and wall time | Generated-token count, elapsed seconds, aggregate tokens/sec, completed-cycle mean | Scope estimates to completed synthetic cycles; do not call them benchmark latency. |
| GPU memory stability | Pre/post-cycle allocated/reserved/peak snapshots and tolerance-based growth description | Report the raw snapshots and any growth; `within_tolerance` is not a proof against all leaks. |
| Activation serialization/storage | Artifact byte sizes, checksums, inspection result, activation-only projections | Projection excludes trace, model-cache, and full-study storage unless separately measured. |
| Resume/restart semantics | `resume_decision`, intent state, and append-only terminal records | Completed, failed, and ambiguous attempts must not be regenerated or replaced. |
| Failure preservation | `model_load_failed`, `intent_failed`, `execution_blocked_cuda`, and unresolved declarations | Preserve every failure/unknown state; do not shorten, retry, or replace it. |
| Tier estimate | Synthetic wall/storage projections at 1,800 / 1,200 / 800 trajectories | A later tier decision must rely only on recorded qualification estimates and must explain any unmeasured components. |
| Terminal conclusion | Explicit pass/blocked/infeasible/not-evaluable classification | Distinguish runtime feasibility from any scientific conclusion. |

## Mock-only verification

No model load or inference is needed to test the harness:

```powershell
python -m unittest discover -s activation_continuation/runtime_qualification/tests -v
```

The tests use fake CUDA probes and fake execution records. They verify the
dry-run default, append-only activation serialization, CUDA blocking before a
runner is prepared, runtime evidence aggregation, and no-retry handling for
completed, failed, and interrupted-unknown intents.
