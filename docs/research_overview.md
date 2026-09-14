# Research overview

## Scope

This repository records a completed Q0–Q7 reproduction and audit of the
released [CoDE-Stop](https://github.com/sudoparsa/CoDE-Stop) confidence
measurement path, a completed M1 Q8_0 measurement-semantics feasibility
study, and M2's runtime-feasibility abort. The older risk-controlled P1
protocol remains frozen and paused at its direct prior-work gate.

Nothing in this repository claims a validated replacement for CoDE-Stop.

## Completed audit

At a CoDE-style reasoning checkpoint, the released path forces a candidate
answer and computes a probability-based confidence measurement. The audit
found that the generated candidate can complete before the released probe
terminates. The released confidence window can therefore include both the
candidate and later continuation text.

Boundary-Aligned Confidence (BAC) changes only the measurement boundary: it
ends the forced trial at the matching outer `\boxed{...}` close and takes the
geometric mean of the pre-specified candidate-token probabilities. It does not
change the reasoning prefix, answer forcing, model, or decoding used for the
comparison.

The completed evidence has three distinct statuses:

- **ESTABLISHED IN CURRENT SANDBOX:** Q3 and the independent Q6 holdout show
  that the released confidence span can include substantial post-answer text.
  Q6’s 79.37% result is a counterfactual reduction in trial-probe generated
  tokens on that holdout, not total inference saving.
- **EXPLORATORY:** BAC had substantially stronger candidate-correctness
  ranking in the Q3 development batch. Q6 had no correct probe candidates, so
  it could not evaluate that ranking.
- **ESTABLISHED PRECISION LIMIT:** Q7 fixed-prefix probes found stronger
  candidate agreement between Q8 and BF16 than between Q4 and BF16. Q4 remains
  a discovery backend, not a final-validation proxy.

## M1 measurement-semantics feasibility

M1 used a preregistered 16-example Qwen3-4B Q8_0 development-feasibility
cohort and shared greedy forced-answer traces. Of 47 completed rollouts, 44
were valid paired A/B endpoint comparisons. In all 44, the released endpoint
continued after the matching outer-box candidate boundary; the median absolute
score difference was 0.119 and the B/A policy-prefix-token ratio was 28.48%.

These are paired measurement and endpoint-accounting results only. They do
not establish a new score, correctness superiority, calibration, a safe
threshold, total cost saving, or a deployed stopping policy. The M1
[terminal decision](m1_forced_answer_measurement_semantics_decision.md)
records both the favorable feasibility gate and its immutable reporting
limitations.

## M2 confirmatory measurement audit

M2 independently froze a 100-example MATH-500 cohort, Q8_0 runtime, greedy
probe path, released terminal behavior, 21-token cap, score definitions, and
fixed confirmation criteria before inference. It did not modify M1 or reopen
P1. Both Q8_0 and BF16 load-only preflights passed, but a Q8 base completion
stalled mid-generation below the configured context and generation limits.
The single-slot server did not recover, so the next base request timed out.

Only 18 primary-valid pairs were produced, versus the fixed minimum of 80;
the BF16 anchor never started. M2 is therefore **EFFECT NOT CONFIRMED — runtime
infeasible**, not evidence that the semantic effect is absent. Its
[frozen protocol](m2_confirmatory_measurement_protocol.md),
[literature gate](m2_confirmatory_literature_gate.md), and
[abort record](m2_runtime_feasibility_abort.md) are public.

## Paused P1 direction

The retained P1 protocol isolates one question: whether an audited
candidate-boundary confidence signal behaves more safely when the decision
threshold is chosen with an upper-risk controller on labeled calibration data.

```text
checkpoint -> forced candidate -> candidate boundary -> BAC
                                             |
                       calibration-set UCB risk control chooses upper threshold
                                             |
                                 untouched-test accuracy / risk / cost
```

The paired comparison would use the same risk-control procedure for the
released full-span signal (`c_full`) and BAC. Their intended difference is the
signal and probe boundary only. The study is paused and is not an authorized
next action. Full historical details are in
[next_study_protocol.md](next_study_protocol.md).

## Related work and overlap boundary

[Conformal Thinking](https://arxiv.org/abs/2602.03814) is the closest
decision-rule reference for P1. It provides a risk-controlled upper-threshold
formulation for confidence-based reasoning decisions. The paused protocol is
an upper-threshold-only application, not a reproduction of its full
dual-threshold method.

[PUMA / Stop When Reasoning Converges](https://arxiv.org/abs/2605.17672)
studies reasoning-level semantic convergence and combines redundancy with
answer-level verification. It is intentionally out of scope: adding that
mechanism would confound the current measurement-signal and decision-rule
question.

[*From token probabilities to calibrated confidence*](https://arxiv.org/abs/2608.07827)
motivates caution in interpreting raw probability magnitude as correctness. It
may become a baseline or reference, but its calibration methods are not merged
into the primary method.

REFRAIN's answer-only boxed-region likelihood rules out a claim that the score
or generic forced-answer stopping is novel. M1 and M2 are instead restricted
to the reproducible question of how the pinned released CoDE-Stop endpoint and
score semantics differ from an exact candidate boundary on a shared trace.
M2's bounded recheck found no public artifact that already performs that exact
audit. This is a narrow overlap check, not an exhaustive literature claim.

## What this project does not claim

The audit does not establish a faithful BF16 reproduction, end-to-end accuracy
improvement, a safe absolute BAC threshold, a new state of the art, or a
published/accepted method. M1 justifies a narrow measurement-audit manuscript
path; M2 does not supply a confirmatory result because its runtime was
infeasible.
