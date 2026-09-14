# Related work boundary

This is a concise overlap check for the completed measurement audit and the
retained, paused P1 protocol, not an open-ended literature review.

## CoDE-Stop

[CoDE-Stop](https://arxiv.org/abs/2604.04930) supplies the released setting:
reasoning checkpoints, forced intermediate answers, token-probability
confidence, and confidence-dynamics stopping. Q0–Q7 and M1 audit the
measurement boundary in its released probe path. The public repository credits
the upstream paper and implementation; it does not redistribute or modify them.

## REFRAIN / Stop When Enough

[Stop When Enough](https://aclanthology.org/2026.acl-long.1256/) explicitly
uses length-normalized likelihood over answer tokens inside a boxed region.
It rules out any claim that answer-only boxed-region geometric-mean likelihood,
or a generic forced-answer stopping method built around it, is new here.
REFRAIN does not provide the same paired audit of the pinned CoDE-Stop terminal
token behavior, 21-token cap, released denominator, and exact outer-box
boundary on a shared greedy trace.

## Conformal Thinking

[Conformal Thinking](https://arxiv.org/abs/2602.03814) provides the closest
decision-rule reference. Its upper-threshold loss and UCB procedure motivated
the retained P1 controller. P1 is paused at a direct prior-work gate; it is not
an authorized next experiment or a claim to reproduce the paper's full method.

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

REFRAIN and Conformal Thinking close broad novelty claims about answer-only
likelihood, forced-answer stopping, and risk-controlled reasoning. M1 and M2
are restricted to a narrower question: whether the pinned released CoDE-Stop
endpoint and score semantics differ from an exact candidate boundary on a
shared trace. M2's bounded pre-inference recheck found no public artifact that
already performs that exact audit. This conclusion is limited to the cited
works; any directly overlapping prior implementation found later must be
documented prominently rather than hidden.
