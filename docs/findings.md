# Findings

## ESTABLISHED IN CURRENT SANDBOX: measurement boundary

Q3 and Q6 show that, in the studied Q4_K_M batches, the released forced probe
can continue after the candidate answer is complete.

| Frozen analysis | Completed boxes before released termination | Post-box released-window NLL share |
| --- | ---: | ---: |
| Q3 development | 60 / 60 | mean 78.61%, median 84.28% |
| Q6 preregistered holdout | 36 / 36 | mean 74.44%, median 72.72% |

On Q6, the median absolute difference between `c_full` and BAC was 0.193568.
Stopping each trial at an already-completed box boundary would change counted
trial-probe generation from 756 to 156 tokens. This is a **79.37%
counterfactual reduction in trial-probe generated tokens on the Q6 holdout**;
it is not total inference saving and does not establish an accuracy change.

## EXPLORATORY: correctness ranking

On frozen Q3 development probes, BAC had stronger correctness-ranking metrics
than the released full-span signal:

| Signal | AUROC | AUPRC | Directly evaluable probes |
| --- | ---: | ---: | ---: |
| Released `c_full` | 0.6894 | 0.4333 | 59 |
| BAC | 0.9981 | 0.9924 | 59 |

This is descriptive development evidence, not a calibrated threshold or a safe
stopping rule. Q6 had 36 directly evaluable candidates, all incorrect, so it
could not estimate a corresponding holdout ranking metric.

## ESTABLISHED IN CURRENT SANDBOX: Q7 precision fidelity

Q7 fixed the reasoning prefix and forced-candidate tokens before comparing
precisions. It is a probe-level fidelity check, not an end-to-end accuracy
benchmark.

| Pair | Fixed paired checkpoints | Exact normalized candidate agreement | BAC Pearson / Spearman |
| --- | ---: | ---: | ---: |
| Q8_0 vs Q4_K_M | 30 | 15 / 30 | 0.856 / 0.922 |
| BF16 vs Q8_0 | 12 | 11 / 12 | 0.995 / 1.000 |
| BF16 vs Q4_K_M | 12 | 5 / 12 | 0.953 / 0.979 |

Q4 BAC rankings were partly aligned with Q8 and BF16, but its candidate
fidelity was not established. The appropriate roles for future work are:

- `Q4_K_M`: historical exploratory/discovery backend.
- `Q8_0`: primary practical validation backend.
- `BF16`: selective fidelity anchor only.

`TQ1_0` was an unusable extreme post-training ternary stress condition: 0 of
32 scheduled probes completed an outer candidate box. It is reported as a
negative result, not as a comparison to BitNet-style trained ternary models.

The compact values are in
[results/q7_precision_summary.json](../results/q7_precision_summary.json).

## ESTABLISHED, NARROWLY: M1 forced-answer measurement semantics

M1 was a separately preregistered 16-example Qwen3-4B Q8_0
development-feasibility study. It completed 47 available shared forced-answer
rollouts; 44 had a closed candidate boundary and passed the paired-integrity
invariant. The released endpoint continued after that boundary in 44/44 valid
pairs. The median absolute `c_full`-minus-boundary-score difference was 0.119,
and 34/44 pairs had an absolute difference of at least 0.05.

At strict illustrative thresholds 0.70, 0.80, 0.90, and 0.95, first-crossing
decisions differed in 2, 7, 13, and 10 of 15 eligible examples. Endpoint
accounting was 783 released-policy-prefix tokens versus 223 boundary-policy-
prefix tokens (B/A = 28.48%). Because A and B came from a shared rollout,
this is not a realized in-run saving, total-task saving, latency result, or
energy result.

The favorable M1 feasibility gate supports only a code-to-paper
measurement-audit manuscript path. Its frozen analyzer did not emit several
promised descriptives, including aggregate candidate agreement, the endpoint-
denominator diagnostic, rank correlation, and timing aggregates; these were
not backfilled after outcomes existed. See the
[M1 terminal decision](m1_forced_answer_measurement_semantics_decision.md)
and [public aggregate digest](../results/m1_result_digest.json).

## NOT CONFIRMED: M2 confirmatory audit

M2 fixed a fresh 100-example cohort and all primary outcomes before inference.
Both precision load-only preflights passed. A Q8_0 base completion then stalled
mid-generation below the configured context and generation limits; the
single-slot server did not recover, and the next request timed out downstream.
The run preserved six completed bases, 18 primary-valid paired checkpoints,
two timed-out bases, and one interrupted-unknown intent. The remaining 91
selected examples were unstarted, and the predeclared BF16 anchor was not run.

The fixed minimum was 80 primary-valid pairs, so M2 is **EFFECT NOT CONFIRMED
— runtime infeasible**. This is not evidence for absence of the measurement
effect and cannot be pooled with M1. No request was retried or replaced. See
the [M2 abort record](m2_runtime_feasibility_abort.md).

## Not established

The completed audit does not establish that BAC improves final-answer accuracy,
that any absolute BAC threshold is safe, that Q4 generalizes to BF16, or that a
new stopping policy improves end-to-end cost. P1 remains paused; M2 did not
reach a confirmatory result. Any future empirical study requires a new,
separately authorized protocol.
