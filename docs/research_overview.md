# Research overview

## Scope

This repository records a completed Q0–Q7 reproduction and audit of the
released [CoDE-Stop](https://github.com/sudoparsa/CoDE-Stop) confidence
measurement path. It then freezes one unrun follow-up study:

> **Boundary-Aligned Confidence under Risk-Controlled Early Stopping**

The follow-up is a protocol, not a result. Nothing in this repository claims a
validated replacement for CoDE-Stop.

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

## Frozen next direction

The next study isolates one question: whether an audited candidate-boundary
confidence signal behaves more safely when the decision threshold is chosen
with an upper-risk controller on labeled calibration data.

```text
checkpoint -> forced candidate -> candidate boundary -> BAC
                                             |
                       calibration-set UCB risk control chooses upper threshold
                                             |
                                 untouched-test accuracy / risk / cost
```

The paired comparison uses the same risk-control procedure for the released
full-span signal (`c_full`) and BAC. Their intended difference is the signal
and probe boundary only. The first study uses no lower/unsolvable threshold,
semantic redundancy, PUMA mechanism, ternary condition, CUSUM, or extra
stopping signal. Full details are in
[next_study_protocol.md](next_study_protocol.md).

## Related work and overlap boundary

[Conformal Thinking](https://arxiv.org/abs/2602.03814) is the closest related
work. It provides a risk-controlled upper-threshold formulation for
confidence-based reasoning decisions and is the source for the proposed UCB
selection procedure. Its forced-answer confidence is not the same as this
audit’s candidate-boundary token span: this work ends at the completed outer
box and scores only the pre-specified candidate tokens. The next study is an
upper-threshold-only application, not a reproduction of Conformal Thinking’s
full dual-threshold method.

[PUMA / Stop When Reasoning Converges](https://arxiv.org/abs/2605.17672)
studies reasoning-level semantic convergence and combines redundancy with
answer-level verification. It is intentionally out of scope: adding that
mechanism would confound the current measurement-signal and decision-rule
question.

[*From token probabilities to calibrated confidence*](https://arxiv.org/abs/2608.07827)
motivates caution in interpreting raw probability magnitude as correctness. It
may become a baseline or reference, but its calibration methods are not merged
into the primary method.

Within these specifically reviewed works, no paper was identified that
implements the exact combination of candidate-boundary token confidence and a
risk-controlled adaptive reasoning threshold. This is a narrow overlap check,
not an exhaustive literature claim. If a direct prior implementation is found,
the study should report the conflict and narrow its contribution accordingly.

## What this project does not claim

The audit does not establish a faithful BF16 reproduction, end-to-end accuracy
improvement, a safe absolute BAC threshold, a new state of the art, or a
published/accepted method. The final paper contribution depends on the next
study completing without violating its preregistered abort conditions.
