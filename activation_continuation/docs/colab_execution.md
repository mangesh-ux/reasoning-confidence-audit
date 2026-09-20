# Colab execution workflow

## Scope and non-negotiable boundary

This package moves only the pre-benchmark GPU execution path to Google Colab.
It does not change the study question, the realized `W -> C` target, the
checkpoint schedule (`256`, `512`, `1024`, `2048`, `3072`), split rules,
statistical design, model, decoding configuration, or scientific gates.

It contains no benchmark runner. The notebook can execute only the frozen,
hand-authored synthetic runtime qualification. A passing qualification is a
runtime result, not a scientific result and not a Tier A/B/C decision.

The earlier local failure remains authoritative provenance in
`activation_continuation/docs/a1_runtime_qualification.md`: CUDA was blocked
in the Codex environment. The Colab report supplements that record; it does
not erase, reinterpret, or replace it.

## Before opening Colab

1. Push the reviewed repository commit to GitHub.
2. In Colab, choose a GPU runtime with BF16 support and at least 16 GiB VRAM.
   An L4 or A100 is appropriate; a T4 will fail the BF16 gate.
3. Open
   `activation_continuation/notebooks/colab_runner.ipynb` from that reviewed
   checkout.
4. In the first settings cell, replace `REPLACE_WITH_REVIEWED_COMMIT_SHA` with
   the exact 40-character commit hash reported by Codex. Do not use a branch
   name such as `main`.
5. Leave `RUN_BENCHMARK_STUDY = False`. The default private root is the
   generic, uncommitted path
   `/content/drive/MyDrive/reasoning_activation_study`. You may change that
   value in the notebook to another private Drive location; never commit that
   user-specific path.

Run the notebook cells in order. The notebook will:

1. mount Google Drive;
2. clone or verify a clean existing checkout, verify its GitHub origin, fetch,
   and detach at the exact requested commit;
3. create an isolated Colab virtual environment and install the explicit
   package-version lock in `configs/requirements-colab.txt`;
4. run `pip check`;
5. invoke the importable preflight module; and
6. print the exact public-safe JSON report emitted by that invocation.

The notebook asserts on any failed preflight. Do not alter the model,
precision, decoding parameters, token budget, synthetic plan, or resource
threshold to make a failure disappear.

## What the preflight verifies

The public report prints an explicit `PASS` or `FAIL` for:

- frozen runtime versions and CUDA build;
- CUDA availability, GPU name, total VRAM, and BF16 support;
- private Drive free space;
- deterministic evaluator fixtures;
- retrieval and verification of `Qwen/Qwen3-1.7B` at revision
  `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`;
- native BF16 model load;
- all-layer last-prefix hidden-state extraction;
- repeated synthetic generation, including the full 4,096-token cap on every
  fixed cycle;
- memory and context evidence; and
- a second resume pass that must skip all completed synthetic intents.

The report also records Python, PyTorch, Transformers, CUDA-build, GPU, VRAM,
the checked-out source commit, the immutable configuration hash, and a
path-free execution-identity hash. A qualification directory is reused only
when that identity, the plan, the source commit, the package versions, and the
GPU identity all match.

Detailed error text is written only under private Drive provenance. The
returnable JSON intentionally contains no Drive path, benchmark text, raw
trace, activation vector, model weight, or token sequence.

## Artifact separation and recovery

The repository checkout under `/content` is for code, configuration,
documentation, and future manifests only. It is never an artifact root.

| Private Drive directory | Contents | Repository status |
| --- | --- | --- |
| `model_cache/` | exact model snapshot and private snapshot provenance | never commit |
| `qualification/` | synthetic plan, append-only ledger, private activations, and execution identity | never commit |
| `private_study/` | future base trajectories, forced-answer records, checkpoint activations, and per-problem receipts | never commit |
| `provenance/` | detailed private diagnostics | never commit |
| `public_safe/` | path-free aggregate preflight reports only | may be reviewed before a deliberate public export |

For future benchmark code, `ImmediateTrajectoryCheckpointStore` must be used
in this sequence for every `(problem_id, rollout_seed)`:

1. durably call `declare_intent` before any model request;
2. run that one trajectory;
3. immediately call `write_completed` after successful generation.

Both declaration and completed-record files are exclusive and fsynced, and
their ledger is append-only. A completed intent resumes as `skip_completed`.
A declaration without terminal evidence is `interrupted_unknown`, so a new
Colab process must preserve it rather than regenerate it. A disconnect can
therefore never require a successful or possibly-successful trajectory to be
replaced.

## What to return after the preflight

Return all of the following to Codex, and nothing private:

1. the printed `COLAB PREFLIGHT REPORT` PASS/FAIL table;
2. the full JSON printed by the next notebook cell (the exact
   `colab_preflight_*.json` filename emitted by the preflight, not merely the
   newest report in the directory);
3. the `Repository checked out at ...` commit line; and
4. any public failure category shown by the notebook.

Do not return or upload hidden activations, raw synthetic output, raw
reasoning traces, benchmark rows, model files, detailed private diagnostics,
or a Drive path.

## Mandatory stop after a PASS

After a passing report, stop and return the material above. Do not set
`RUN_BENCHMARK_STUDY` to true and do not create a benchmark artifact.

The synthetic estimate covers the executed synthetic activation path and peak
VRAM; it cannot by itself select a scientific compute tier because full-study
cost also includes two base rollouts per problem, question-only activations,
up to five absolute checkpoints, forced-answer artifacts, and private trace
storage. Tier A/B/C must later be selected solely from a documented
post-qualification full-study cost estimate, before any benchmark call.

When a future study manifest exists, the hard gate requires its declared
canonical SHA-256 (calculated over the manifest with `manifest_sha256`
omitted), an execution binding to the accepted preflight/config/source/model,
and an explicit Tier A/B/C decision with positive projected total runtime,
private disk, and peak-VRAM estimates. The gate remains intentionally unable
to generate a benchmark trajectory on its own.
