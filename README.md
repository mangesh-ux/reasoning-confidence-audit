# Reasoning Confidence Audit

> An audit tied to an exact upstream
> [CoDE-Stop commit](https://github.com/sudoparsa/CoDE-Stop/tree/b5081e7c2abe23bb1d19649421cc13522fee7c50),
> asking how it measures confidence after requesting an answer.

## In one paragraph

This repository asks a narrow reproducibility question: when a released
early-stopping implementation asks a reasoning model for an answer and turns
the generated token probabilities into a confidence-like score, **which text
does that score actually describe?** In the audited CoDE-Stop revision, the
answer-producing continuation can continue after the first complete boxed
answer. Its released score can therefore include both that first boxed answer
and later generated continuation. This repository compares that released
measurement span with a span ending at the completed boxed answer. Its
completed record combines offline accounting of previously recorded,
unmodified traces with a controlled comparison that repeats the same
deterministic generation. It is a
measurement-semantics audit—not a new confidence metric, stopping controller,
calibration method, accuracy result, or demonstrated end-to-end saving.

The public release contains aggregate results, exact revision identifiers,
protocols, synthetic tests, and reusable parsing/scoring utilities. It intentionally
excludes model weights, benchmark rows, raw reasoning traces, raw token
log-probability traces, binaries, and upstream source code.

## Core terms

The following project-specific terms are defined before their first use in the
technical sections below.

| Term | Meaning in this audit |
| --- | --- |
| **Pinned release** | The exact upstream CoDE-Stop revision under audit: [`b5081e7c2abe23bb1d19649421cc13522fee7c50`](https://github.com/sudoparsa/CoDE-Stop/tree/b5081e7c2abe23bb1d19649421cc13522fee7c50). “Released” means this implementation behavior, which can be more specific than the paper’s prose or equations. |
| **Reasoning prefix** | Tokens the model has already generated while solving a problem, before an answer is elicited. |
| **Checkpoint** | A preselected point in that reasoning prefix at which the audit starts an answer probe. It is fixed in advance, not a learned stopping decision. |
| **Forced-answer probe** | A greedy continuation from a checkpoint using a fixed cue that asks the model to produce a boxed answer. The parser expects the first nonempty generated text to begin with `{...}`; the audit represents the resulting candidate as `\boxed{...}`. It measures a candidate; it is not necessarily the model’s final deployed output. |
| **Candidate answer and boundary** | In a forced probe, the audit represents the generated brace expression as a syntactically complete outer `\boxed{...}` expression. The boundary is its matching closing outer brace. |
| **Released full-span confidence (`c_full`)** | The probability aggregate reconstructed from the released probe’s configured generated span. That span can extend past the candidate boundary. It is a confidence-like likelihood aggregate, not a calibrated probability of correctness. |
| **Boundary-Aligned Confidence (BAC)** | This project’s descriptive name for the ordinary geometric mean of token probabilities inside the candidate boundary only. The calculation is not new; BAC is a comparison instrument, not a proposed metric or stopping policy. |
| **Shared greedy pair** | In the paired studies described below, a released-endpoint and candidate-boundary measurement derived from the same prompt, reasoning prefix, cue, and deterministic greedy rollout. Only endpoint semantics and accounting differ. |
| **Valid shared pair** | A shared pair meeting the frozen integrity rule for the study in which it is used. Invalid, malformed, and unavailable outcomes are retained rather than repaired. The confirmatory protocol uses the stricter term **primary-valid** for pairs that also satisfy its predeclared agreement and finite-score checks. |
| **Counterfactual token accounting** | An offline count of probe tokens that would not have been generated had an already-closed candidate boundary ended the probe. It is not observed whole-task token saving, latency, or energy use. |

**Parser convention.** The forced-probe parser expects the generated suffix
above, treats escaped braces as structural, and tracks nesting. The offline
audit parser instead attempts the first `\boxed` marker in decoded text and
ignores escaped braces. Both report malformed or no-close outcomes rather than
repairing them; see the
[package README](src/README.md).

**Exact score convention.** Let `q_j` be the selected probability for
one-based generated token `j`, and let `n` be the released endpoint’s
selected-token count. The
released reconstruction is
`c_full = exp((sum_{j=2}^{n-1} log q_j) / (n - 1))`: its numerator excludes
the first and last selected tokens while its denominator remains `n - 1`. BAC
is `exp(mean(log q_j))` over only the token positions strictly between the
token pieces containing the opening and matching closing outer braces. These
are likelihood aggregates, not calibrated probabilities of correctness.

## The audited comparison

The completed record uses two designs: offline boundary accounting on previously
recorded, unmodified released traces, and a controlled matched-rollout comparison. The diagram
shows the latter. At a fixed point in an already-generated reasoning trace,
the controlled comparison holds the prompt, reasoning prefix, answer cue, and
greedy decoding path fixed, then compares only where the resulting probability
aggregate ends.

```text
reasoning prefix
      │
      ├── checkpoint ── forced-answer probe ── first complete \boxed{...}
      │                                      │
      │                                      ├── candidate-only endpoint → BAC
      │                                      │
      │                                      └── later continuation → released c_full
      │
      └── repeat at frozen checkpoints
```

For the forced-probe comparison, the candidate boundary is the matching closing
brace of the first outer `\boxed{...}` expression. It handles nested braces,
but it is a fixed parser convention for this audit—not a general mathematical-
answer extractor.

## Precision labels

`Q4_K_M` and `Q8_0` are GGUF (llama.cpp model-file) quantizations of the
studied model: respectively a 4-bit and an 8-bit format. `BF16` (bfloat16) is
a higher-precision floating-point fidelity anchor. They are not different model
architectures. Q4_K_M is retained only as the historical exploration backend,
Q8_0 is the practical validation backend, and BF16 is a small fixed-prefix
anchor rather than a throughput-matched reproduction.

## Study map and current status

The labels below are internal study identifiers, not benchmark names or model
versions.

| Label | What it is | Current status and permitted interpretation |
| --- | --- | --- |
| **Q0–Q7** | Historical source-pinned reproduction and audit stages. | Frozen. Q4_K_M findings are discovery evidence; Q7 is a fixed-prefix precision check, not end-to-end model fidelity. |
| **M1** | Preregistered 16-example Q8_0 paired measurement-feasibility study. | Completed. It supports a narrow measurement-audit finding, not a new score, controller, or deployment claim. |
| **M2** | Preregistered 100-example Q8_0 confirmation attempt. | Runtime-infeasible after 18 primary-valid paired checkpoints, below its fixed minimum of 80. This is neither positive evidence nor a null-effect result. |
| **L1** | Synthetic, source-to-equation audit of the pinned implementation. | Completed formal reproducibility evidence only; no model, benchmark, or inference was used. |
| **P1** | Retained risk-controlled follow-on protocol. | Frozen and paused at a direct prior-work gate; no P1 inference is authorized. It is not a result. |

Three individual frozen stages are named below: **Q3** is the development
probe batch, **Q6** is the independent preregistered holdout, and **Q7** is the
fixed-prefix precision comparison.

## What the evidence supports

### Established within the stated scope

- **Released measurement spans can extend past a completed candidate.** In Q3
  (the historical Q4_K_M development batch) and Q6 (the preregistered
  holdout), released probes contained post-boundary continuation in their
  scored span. This is a measurement-span result, not a claim that CoDE-Stop
  is inaccurate.
- **M1 reproduced the endpoint difference under Q8_0.** In a preregistered
  16-example development-feasibility study, all **44/44 valid shared pairs**
  continued after the matching candidate boundary. The median absolute
  `c_full`–BAC difference was `0.119`; 34/44 pairs differed by at least `0.05`.
  These are paired measurement results only.
- **The Q6 token result is strictly counterfactual.** Ending an already-closed
  candidate boundary would reduce counted forced-answer probe generation from
  756 to 156 tokens: a **79.37% counterfactual reduction in probe tokens** on
  that holdout. It is not a measured end-to-end saving.
- **Q8_0 was closer to BF16 candidate identity than Q4_K_M** on Q7’s frozen
  fixed-prefix subset: 11/12 candidate strings matched exactly after the
  audit’s fixed text normalization for BF16–Q8_0, versus 5/12 for
  BF16–Q4_K_M. This is probe-level candidate fidelity only.
- **L1 formalized released implementation semantics.** On its valid domain,
  the pinned release’s default degeneration component—a history-based
  stop-trigger component—reduces to a recency-weighted count of strict
  decreases in log confidence on scores first clamped to a fixed floor, after
  an initial warm-up. This is a source-level result, not evidence
  that changing the equation improves a policy. See the
  [L1 decision record](docs/l1_equation_to_execution_decision.md).

### Exploratory only

On the frozen Q3 development probes, BAC ranked candidate correctness more
strongly than `c_full`. That result is exploratory: the independent Q6 holdout
had no correct directly evaluable probe candidates, so it could not evaluate
the same ranking question. No absolute BAC threshold is established as safe.

### Not confirmed

M2 could not complete its confirmatory audit because the pinned Q8_0 runtime
stalled mid-generation and its one-request-at-a-time local server did not
recover. The study produced 18 primary-valid paired checkpoints, below its
predeclared 80-pair minimum; its BF16 anchor did not begin. The correct classification is **EFFECT NOT
CONFIRMED — runtime infeasible**. See the [M2 abort record](docs/m2_runtime_feasibility_abort.md).

## Verify this public release

**Requirements:** CPython 3.10+ and a checkout of this repository. The public
checks use the standard library only. They do not download a model, start
llama.cpp, contact a server, or access benchmark rows.

```powershell
$env:PYTHONPATH = "src"
python -B -m unittest discover -s tests -v
python examples\synthetic_probe_demo.py
python src\rebuild_public_results.py --output results\rebuilt_aggregate_results.json
```

Expected behavior:

- the synthetic suite passes (**34 tests** at this release);
- the demo prints a candidate-only versus released-full-span example; and
- the result packager writes a compact aggregate JSON file and reports its
  SHA-256.

These commands verify the public reconstruction and aggregate packaging. They
do **not** reproduce historical model inference. `requirements.txt` is not
required for the commands above.

If you have authorized access to the separate frozen artifact tree, the
packager can rebuild the compact public result summary from its aggregate JSON
files:

```powershell
python src\rebuild_public_results.py --artifact-root <path-to-frozen-artifacts> --output <output-path>
```

It reads no weights and starts no inference runtime. A full historical rerun
requires the upstream repositories, model and dataset terms, exact revisions,
and suitable hardware; see [docs/environment.md](docs/environment.md).

## What is implemented here

`src/reasoning_confidence/` is a small, standard-library audit package. It
contains:

- candidate-boundary parsing with nested-brace and malformed-output handling;
- released full-span reconstruction and candidate-only BAC calculation;
- released-style checkpoint token-ID membership utilities;
- source-pinned synthetic reconstructions of score, degeneration, ramp, cap,
  terminal membership, and stop semantics; and
- helpers for candidate agreement, paired comparisons, and probe-token
  accounting.

The package does not contain an automatic model runner, upstream CoDE-Stop
code, raw study artifacts, or a claim to reproduce Q0–Q7 end-to-end. See the
[package boundary](src/README.md) and [methodology](docs/methodology.md).

## Repository map

| Path | Purpose |
| --- | --- |
| [`docs/`](docs/) | Public protocols, decisions, methods, findings, limitations, and related-work boundaries. |
| [`results/`](results/) | Compact aggregate metrics and provenance only. |
| [`src/`](src/) | Standard-library audit utilities and result packager. |
| [`tests/`](tests/) | Offline synthetic tests; no model, GPU, dataset, or network is required. |
| [`examples/`](examples/) | A synthetic released-span versus candidate-boundary demonstration. |
| [`activation_continuation/`](activation_continuation/) | Separate, frozen runtime-qualification support package; it is not a benchmark runner. |

## Provenance and reproducibility boundary

| Item | Publicly recorded scope |
| --- | --- |
| Upstream method | CoDE-Stop commit [`b5081e7c2abe23bb1d19649421cc13522fee7c50`](https://github.com/sudoparsa/CoDE-Stop/tree/b5081e7c2abe23bb1d19649421cc13522fee7c50) |
| Historical model | `Qwen/Qwen3-4B` at revision `1cfa9a7208912126459214e8b04321603b3df60c` |
| Historical runtime | llama.cpp commit `7798007a29a90e3053e799394da48cf53a2f8e0f` |
| Public data policy | Aggregate metrics and provenance only; no raw trajectories, token log-probabilities, benchmark rows, weights, or binaries |
| Detailed provenance | [results/artifact_provenance.json](results/artifact_provenance.json) and [docs/environment.md](docs/environment.md) |

## Separate runtime qualification package

`activation_continuation/` is intentionally separate from the completed audit
evidence. It is a frozen, non-benchmark Colab handoff for checking whether a
specified activation-continuation runtime can execute and recover correctly.
A passing qualification is a runtime result only: it does not authorize
benchmark generation, alter M1/M2/L1, or resume P1. See the
[Colab workflow](activation_continuation/docs/colab_execution.md).

## Deliberately out of scope

This repository does **not** claim:

- a faithful BF16 reproduction or whole-model Q4-to-BF16 generalization;
- a new confidence score, early-stopping algorithm, or calibrated threshold;
- improved final-answer accuracy, a safe stopping policy, or a new state of
  the art;
- observed total token, latency, energy, or end-to-end compute savings; or
- a completed confirmatory M2 result, cross-model result, or publication.

The viable paper story is a narrow, reproducible code-to-paper measurement
audit. Its evidence and limitations are intentionally recorded together in
[docs/findings.md](docs/findings.md), [docs/limitations.md](docs/limitations.md),
and [docs/publication_scope.md](docs/publication_scope.md).

## Suggested reading paths

| Goal | Read |
| --- | --- |
| Understand the source-to-equation semantic audit | [L1 protocol](docs/l1_equation_to_execution_protocol.md) and [L1 decision](docs/l1_equation_to_execution_decision.md) |
| Inspect the main paired evidence | [M1 decision](docs/m1_forced_answer_measurement_semantics_decision.md) and [findings](docs/findings.md) |
| Understand the failed confirmation attempt | [M2 protocol](docs/m2_confirmatory_measurement_protocol.md) and [abort record](docs/m2_runtime_feasibility_abort.md) |
| Reuse the public utilities | [package README](src/README.md) and [`tests/`](tests/) |
| Review the paused follow-on direction | [research overview](docs/research_overview.md) and [next-study protocol](docs/next_study_protocol.md) |

## References

- Parsa Hosseini, Sumit Nawathe, Mahdi Salmani, Meisam Razaviyayn, and Soheil
  Feizi. [*Early Stopping for Large Reasoning Models via Confidence
  Dynamics*](https://arxiv.org/abs/2604.04930), 2026. Upstream implementation:
  [sudoparsa/CoDE-Stop](https://github.com/sudoparsa/CoDE-Stop).
- [*Conformal Thinking: Risk Control for Reasoning on a Compute Budget*](https://arxiv.org/abs/2602.03814),
  2026. Related risk-control reference only.
- Sun et al. [*Stop When Enough: Adaptive Early-Stopping for Chain-of-Thought
  Reasoning*](https://aclanthology.org/2026.acl-long.1256/), 2026. REFRAIN
  already uses answer-only boxed-region geometric-mean likelihood; this audit
  does not claim that score or generic forced-answer stopping as new.

See [CITATION.cff](CITATION.cff) and
[licenses/UPSTREAM_NOTICES.md](licenses/UPSTREAM_NOTICES.md) for citation and
license details.
