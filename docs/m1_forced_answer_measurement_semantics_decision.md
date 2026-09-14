# M1 terminal decision: Measurement-paper path justified

**Decision date:** 2026-09-13
**Decision:** **Measurement-paper path justified.**

This is a narrow decision about a reproducibility and measurement-semantics
paper path. It is not a decision that Boundary-Aligned Confidence (BAC) is a
new confidence metric, that any threshold is safe, that BAC improves
correctness, or that a stopping controller saves end-to-end inference cost.
It does not reopen P1, modify CoDE-Stop, or authorize further model inference.

## What completed

M1 executed the preregistered Q8_0-first development-feasibility design in
the privately retained frozen protocol.
The non-output-selected MATH-500 development sample contained 16 examples.
The execution completed all 16 base trajectories and 47 available paired
shared A/B forced-answer rollouts. One otherwise possible checkpoint was
unavailable because its base continuation was short; it was not replaced.

Of the 47 completed rollouts, 44 completed the candidate boundary and passed
the runner's A/B integrity invariant. Three did not yield a closed B boundary
and remain represented as such; no rows, checkpoints, or outputs were
replaced. The passing load-only preflight used the frozen Qwen3-4B Q8_0
configuration at context 4096 and issued zero completion requests.

The ignored private outcome artifacts are bound by these SHA-256 values, which
are sufficient to detect a changed artifact without exposing benchmark rows,
reasoning traces, token sequences, binaries, paths, or model outputs:

| Private artifact | SHA-256 |
| --- | --- |
| Passing load-only preflight outcome | 9d4a1945187c92d5d1c69fb35786969e2aa802cf9e4e98e2d33fef64d4e33eaf |
| Completed run summary | 5e8d091b6b776fa5a77fc00f4e464896361ce0556f3328b5fb474f4c2a03678d |
| Preregistered analysis output | 50465875eee903c6c23ffe7a8ad794b0bbdbe6965bcb8285917b542b79846642 |

The public-safe aggregate mirror is
[m1_result_digest.json](../results/m1_result_digest.json). It is not a
substitute for a future release audit.

## Predeclared feasibility evidence

The results establish a paired semantic difference in this bounded execution:

| Predeclared quantity | Result | Interpretation boundary |
| --- | ---: | --- |
| Valid A/B integrity pairs | 44 | The runner's shared-prefix invariant held for each valid pair. |
| Valid pairs with A continuation after B close | 44 / 44 | The released-style endpoint continued after the matched candidate boundary in every valid pair. |
| Post-boundary A tokens | median 17; mean 12.73 | Token-span result only. |
| Absolute c_full minus BAC difference | median 0.119; 34 / 44 at least 0.05 | A score-semantic difference, not a calibration or safety result. |
| Different first illustrative threshold crossing | 2, 7, 13, and 10 of 15 eligible examples at thresholds 0.70, 0.80, 0.90, and 0.95 | Fixed, strict-greater-than illustrative decisions only; not a deployed policy. |
| A/B policy-prefix tokens | A: 783; B: 223; B/A: 28.48% | Endpoint accounting under the shared rollout, not total task cost or an observed in-run saving. |

All four automatic feasibility criteria passed: at least 24 valid pairs;
continuation in at least 25% and at least six pairs; all three predeclared
practical-effect criteria; and B policy-prefix tokens no greater than 75% of
A. The literature criterion is resolved by the revalidation below.

Correctness is descriptive only. The fixed evaluator classified 38 paired
candidates as evaluable (22 correct, 16 incorrect) and six as
not-evaluable-empty-parse. The small development sample produced different
point estimates for c_full and BAC, but it also contained high-confidence
wrong candidates under both signals, including BAC at the highest fixed
threshold. It supports neither a correctness-superiority claim nor a safe
absolute-threshold claim.

## Literature revalidation

The literature and public-code audit was repeated on 2026-09-13. The
CoDE-Stop paper does not fully identify the exact forced-probe termination,
candidate parser, endpoint exclusions, or token accounting; its pinned
repository specifies code-level behavior for several of these details but has
no matching outer-box candidate parser. The recheck also reconfirmed that
Conformal Thinking establishes broad risk-controlled reasoning but does not
provide the public probe generator needed to make its full condition
executable. See [CoDE-Stop](https://arxiv.org/html/2604.04930), the pinned
[CoDE-Stop source](https://github.com/sudoparsa/CoDE-Stop/tree/b5081e7c2abe23bb1d19649421cc13522fee7c50),
[Conformal Thinking](https://arxiv.org/html/2602.03814), and its public
[repository](https://github.com/xidulu/reasoning_risk_control).

The recheck found a material scope constraint that was not in the original
M1 audit: Sun et al.'s ACL 2026
[Stop When Enough](https://aclanthology.org/2026.acl-long.1256/) explicitly
uses a length-normalized geometric-mean likelihood over answer tokens inside a
boxed region. That precludes any claim that M1 invented answer-only likelihood,
BAC aggregation, generic forced-answer stopping, or an associated
accuracy/efficiency method. Its REFRAIN controller is a different method
based on reflective/redundancy cues and sliding-window UCB; it does not
empirically audit the pinned CoDE-Stop code's token-ID terminal rule,
21-token cap, endpoint denominator, or paired released-versus-boundary
rollout. The residual contribution is therefore only a code-to-paper,
artifact-grounded measurement audit.

The recheck also preserves the earlier exclusions: protocol sensitivity is
already broadly studied by [Kim and Kang](https://arxiv.org/html/2605.27752),
and forced completion/redundant reasoning is already studied by
[Datta et al.](https://arxiv.org/html/2604.22266). No primary public source
located in this recheck supplied the same pinned-CoDE released-code-to-exact-
candidate-boundary paired result.

## Analysis-reporting limitations

The immutable run artifacts remain intact, but the committed preregistered
analyzer did not emit several descriptive fields promised by the protocol:

1. the aggregate A/B exact-candidate-agreement summary;
2. the c_boundary_release_denominator diagnostic;
3. paired score rank correlation;
4. shared-trace token and timing aggregates; and
5. paired percentage policy-prefix reduction.

The runner itself checked the A/B integrity invariant for the 44 valid pairs,
and the gate does not depend on the omitted descriptive fields. Still, their
absence is a reporting limitation. It was found only after outputs existed;
the analyzer, thresholds, protocol, and run artifacts were not changed and no
post-output replacement analysis was performed. The aggregate B/A
policy-prefix ratio reported above is the one field the frozen analyzer did
emit; it must not be restated as a physically realized paired saving.

Other non-negotiable limits remain:

- Condition C remains non-executable because its public source does not
  specify a complete rollout/parser/cap/accounting procedure.
- The evaluator is math_verify 0.9.0 with a fixed outer 15-second worker
  timeout, not the upstream MATH-500 model-graded evaluator.
- This is a 16-example development-feasibility study, not a held-out test,
  cross-model result, calibration study, risk-control study, or end-to-end
  efficiency experiment.
- The original verbosity-3 load-only preflight issued zero completions but
  lacked the required residency evidence; its overwritten diagnostic cannot
  be reconstructed. The later immutable verbosity-4 preflight passed before
  any generation.

## Meaning of the decision

The gate supports preparing a narrowly framed measurement-audit manuscript:
the paper may examine how a named released forced-answer implementation's
endpoint and scoring span differ from a candidate-boundary interpretation,
and release a public-safe reproduction harness after a separate release
audit. It must position answer-only likelihood as prior art and must retain
the analysis omissions and all nonclaims above.

Any expanded study, corrected or additional analysis, publication package,
P1 calibration, test inference, new metric, or new controller requires a
separate preregistration and explicit authorization. P1 remains paused.
