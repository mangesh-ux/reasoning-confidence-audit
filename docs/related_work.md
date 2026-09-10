# Related work boundary

This is a concise overlap check for the next study, not an open-ended
literature review.

## CoDE-Stop

[CoDE-Stop](https://arxiv.org/abs/2604.04930) supplies the released setting:
reasoning checkpoints, forced intermediate answers, token-probability
confidence, and confidence-dynamics stopping. The completed Q0–Q7 work audits
the measurement boundary in its released probe path. The public repository
credits the upstream paper and implementation; it does not redistribute or
modify them.

## Conformal Thinking

[Conformal Thinking](https://arxiv.org/abs/2602.03814) provides the closest
decision-rule reference. Its upper-threshold loss and UCB procedure motivate
the frozen next-study controller. The proposed integration is deliberately
narrow: candidate-boundary token confidence is paired with that upper-only
controller. It does not adopt the paper’s lower/unsolvable threshold or claim
to reproduce its full method.

## PUMA / Stop When Reasoning Converges

[PUMA](https://arxiv.org/abs/2605.17672) studies reasoning-level semantic
convergence and already combines redundancy with answer-level verification. It
is intentionally out of scope. Adding those mechanisms would confound the
current question of whether confidence should be measured at the candidate
boundary and how its upper threshold should be selected.

## From token probabilities to calibrated confidence

[*From token probabilities to calibrated confidence*](https://arxiv.org/abs/2608.07827)
motivates caution in treating raw token probabilities as correctness. It may
serve as a future baseline or reference. Its calibration procedures are not
merged into the primary method in this study.

## Novelty/overlap conclusion

Among these specifically reviewed works, no paper was identified that
implements the exact pairing of candidate-boundary token confidence and a
risk-controlled adaptive reasoning threshold. Conformal Thinking is the
closest overlap because it already supplies risk-controlled confidence-based
reasoning decisions. This conclusion is limited to the cited works; any
directly overlapping prior implementation found later must be documented
prominently rather than hidden.
