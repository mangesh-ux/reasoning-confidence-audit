# Activation-continuation study

## Status

**Terminal before benchmark inference — compute infeasible in the current
execution environment.** The required native-Transformers BF16 runtime could
not begin its synthetic qualification because the operating system blocks GPU
access. No target-model, dataset, benchmark, trajectory, activation, training,
validation, or test artifact was created.

The literature gate remains useful: the exact realized, within-problem
continuation-gain measurement is not directly preempted, but recent work
preempts a broad activation-guided stopping-method claim. Any resumed work
must be framed as a controlled validity study and must repeat the runtime gate
after CUDA access is restored.

## Records

- `docs/a0_literature_gap.md` records the primary-source gate and claim
  boundary.
- `docs/a1_runtime_qualification.md` records the terminal preflight evidence.
- `docs/colab_execution.md` documents the separate, Drive-backed Colab
  qualification handoff. It preserves the local A1 record and remains hard
  stopped before benchmark generation.
- `answer_evaluation/` contains deterministic, fixture-tested evaluation
  scaffolding that preserves non-evaluable and error states.
- `runtime_qualification/` contains an opt-in, synthetic-only, local-model
  harness with append-only intent/resumption semantics. It has not executed a
  model in this study.

This namespace is isolated from frozen Q0--Q7, M1, M2, L1, P1, and CoDE-Stop
artifacts. The `.gitignore` deliberately excludes raw traces, activations,
model caches, and other private runtime output from a future public release.
