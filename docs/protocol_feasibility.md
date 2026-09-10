# Protocol feasibility correction

## Why the original calibration plan could not work

The first next-study draft proposed 20 calibration examples with `delta = 0.10`
and primary targets `epsilon = 0.05` and `0.10`. Its pointwise Hoeffding UCB
was:

```text
R_UCB = R_hat + sqrt(log(1 / delta) / (2 * n))
```

Even with zero empirical wrong-early-exit risk, certification requires:

```text
sqrt(log(1 / delta) / (2 * n)) <= epsilon
n >= log(1 / delta) / (2 * epsilon^2)
```

At `delta = 0.10`, this gives:

| Target risk | Minimum calibration size for zero empirical risk |
| --- | ---: |
| `epsilon = 0.10` | 116 |
| `epsilon = 0.05` | 461 |

For the original `n = 20` proposal, the correction alone was approximately
`sqrt(log(10) / 40) = 0.2399`. Neither original target could therefore be
certified, even if calibration observed no wrong early exits.

## Pre-inference correction

No MATH500 inference has been run. The design is corrected before execution,
not after experimental results:

- 200 deterministically selected MATH500 examples;
- 100 calibration and 100 untouched test examples;
- `delta = 0.10`;
- primary `epsilon = {0.15, 0.20}`.

With `n = 100`, the pointwise correction is approximately
`sqrt(log(10) / 200) = 0.1073`. A target of `0.15` permits empirical risk up to
about `0.0427`; a target of `0.20` permits empirical risk up to about `0.0927`.
The corrected protocol preserves explicit abort conditions if calibration still
lacks label variation, has no feasible threshold, fails required monotonicity,
or cannot produce an evaluable loss table.

The corrected executable plan is in
[next_study_protocol.md](next_study_protocol.md).
