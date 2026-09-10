# Publication scope

## Intended story

This project begins as a reproduction and audit of confidence-based early
stopping for reasoning models. The planned paper story is deliberately narrow:

1. Reproduce and audit the released CoDE-Stop confidence measurement.
2. Identify a measurement-boundary problem: forced probes can continue after a
   candidate answer is complete, and that continuation can enter the measured
   confidence span.
3. Show that ending the trial at candidate completion removes large amounts of
   irrelevant trial-probe generation in the audited Q6 accounting.
4. Show that boundary-aligned confidence has useful development-set signal,
   while raw absolute thresholds can still be unsafe.
5. Combine the fixed boundary measurement with a principled, upper-threshold
   risk-control selection rule.
6. Evaluate the resulting accuracy, compute, and wrong-early-exit trade-off on
   an untouched test set.

## Evidence boundary

Steps 1–4 are supported only to the extent documented by the completed Q0–Q7
artifacts. The Q6 79.37% finding is a counterfactual reduction in trial-probe
generated tokens on that holdout; it is not total inference saving. Q3’s strong
BAC ranking is exploratory, because the independent Q6 holdout had no correct
probe candidates. Q7 shows that Q8 is a stronger practical fidelity backend
than Q4 for the observed fixed-prefix candidates, not that Q4 generalizes to
BF16.

Step 5 is a proposed integration, not an established result. The frozen
20-example calibration/UCB design has a known feasibility limitation at the
pre-specified `epsilon` values and may terminate as underpowered before test
inference. That outcome should be reported honestly rather than repaired
post-hoc.

## Relationship to prior work

CoDE-Stop supplies the released checkpoint-and-forced-answer setting.
Conformal Thinking supplies the upper-threshold risk-control reference.
The candidate-boundary measurement is the narrow integration point. PUMA’s
semantic redundancy and answer-level verification are intentionally excluded,
as are token-probability calibration methods from the calibration-related work.
The final paper must state this boundary and disclose any subsequently found
direct-overlap work.

## Publication standard

The eventual contribution depends on the next study succeeding under its
predeclared protocol. Until then, this is not a claim of a new state of the
art, improved CoDE-Stop accuracy, a faithful BF16 reproduction, a TMLR
submission, an accepted publication, or a validated new stopping method.
