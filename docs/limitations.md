# Limitations

## Scope of the completed evidence

The completed work is bounded to the recorded Qwen3-4B revision, prompts,
checkpoint semantics, datasets, local runtime, quantization artifacts, and
small sample sizes. The Q3 development trajectories are correlated within
problem, and Q6 evaluates a small independent holdout rather than a broad
benchmark.

Q6 contained zero correct directly evaluable probe candidates. It therefore
replicated the measurement-boundary issue but could not validate BAC’s
correctness ranking, calibration, final-answer accuracy, or a stopping
threshold on holdout data.

## Q7 precision boundary

Q7 held prefixes fixed and compared forced probes. It did not run a full
reasoning benchmark under every precision. BF16 covered a predefined subset of
12 checkpoints and can serve only as a selective fidelity anchor. The result
that Q8 matched BF16 more often than Q4 on that subset supports choosing Q8 as
the practical validation backend; it does not prove global fidelity or make Q4
results generalize to BF16.

The TQ1_0 branch was CPU-only in the pinned build and produced no completed
candidate boxes across 32 probes. It is an unusable post-training ternary
stress condition, not evidence about trained ternary models.

## Interpretation boundary

BAC is a probability measurement, not a guarantee of correctness. The audit
found high-confidence wrong candidates, so raw absolute thresholds may be
dangerously overconfident. The proposed risk-controlled study is not yet a
result and must not be described as a validated method.

The Q6 79.37% number is a counterfactual reduction in trial-probe generated
tokens on that holdout. It is not a 79% total-inference reduction, latency
measurement, energy measurement, or end-to-end accuracy result.

## Release boundary

This public layer intentionally excludes model weights, converted GGUFs,
binaries, raw reasoning trajectories, raw logprob traces, benchmark rows, and
upstream source code. It does not claim a faithful BF16 reproduction, a new
state of the art, an accepted publication, a TMLR submission, or an accuracy
improvement over CoDE-Stop.
