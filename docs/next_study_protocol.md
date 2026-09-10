# Next-study protocol: Boundary-Aligned Confidence under Risk-Controlled Early Stopping

**Status: protocol frozen; do not execute in this repository update.**

## 1. Research question and boundary

This is one bounded practical local study, not an exact 32K-token reproduction
of any upstream paper:

> Does Boundary-Aligned Confidence (BAC), paired with an upper-threshold
> risk-control rule, offer a safer accuracy/compute trade-off than the released
> CoDE-Stop confidence measurement under the same controller?

The study uses no lower/unsolvable threshold, semantic redundancy, PUMA,
ternary quantization, CUSUM, or additional stopping signal. BAC is fixed before
any new result: the geometric mean of the pre-specified candidate-answer token
probabilities, with the trial ending at the matching outer `\boxed{...}` close.

## 2. Frozen model, data, and split plan

| Item | Pre-specified choice |
| --- | --- |
| Primary model | Qwen3-4B `Q8_0` |
| Q8_0 SHA-256 | `0d5964f2837d157bf8d845f09b006254b85389ef4293ec0f41dd8ffeab1ab3f0` |
| BF16 role | Fidelity-only subset; never used for threshold selection or primary claims |
| BF16 SHA-256 | `89ee1fd110158671b341bf4a8d45bd4859f60ac1ef7252e89233d2492f712814` |
| Q4_K_M role | Historical exploratory baseline only; not a primary validation model |
| Benchmark | MATH500 test split |
| Study size | 60 examples: 20 calibration, 40 untouched test |
| Maximum reasoning budget | 8,192 generated reasoning tokens per problem |
| Runtime source | llama.cpp `7798007a29a90e3053e799394da48cf53a2f8e0f` |

Before **any** model call, resolve and record the exact MATH500 dataset revision,
dataset fingerprint or content SHA-256, license information, schema, and
source URL. This repository does not download the dataset or freeze the 60
rows during the present documentation task.

The selection rule is fixed now. From all valid rows in the pinned test split,
form a row key from its source row index and SHA-256 of normalized problem
text. Rank rows by:

```text
SHA256("BAC_RC_MATH500_SELECTION_V1|<dataset-revision>|<row-index>|<problem-sha256>")
```

Take the first 60. Independently rank those 60 by:

```text
SHA256("BAC_RC_MATH500_SPLIT_V1|<dataset-revision>|<row-index>|<problem-sha256>")
```

Assign the first 20 to calibration and the remaining 40 to untouched test.
Problem content, reference answer, category, earlier model output, correctness,
and confidence must not influence selection or split assignment. Write and
SHA-256 a manifest containing all row keys, problem hashes, split labels,
selection salts, and source provenance before inference. Do not inspect or
generate test-set model output until calibration either selects a threshold or
triggers an abort condition.

For the BF16 fidelity anchor, independently rank calibration and test rows by:

```text
SHA256("BAC_RC_MATH500_BF16_V1|<dataset-revision>|<row-index>|<problem-sha256>")
```

Take four from calibration and four from test. Freeze this eight-example
manifest before inference. It is not used to choose thresholds or report
primary accuracy/risk.

## 3. Frozen runtime and decoding semantics

Before execution, record model and binary SHA-256 values, GPU/CPU placement,
driver version, tokenizer/model revision, context size, prompt template, seed,
temperature, top-p, top-k, and all other decoding settings. Greedy candidate
generation must use temperature 0 with the same base-prompt token IDs,
reasoning-prefix token IDs, and forced suffix token IDs for paired conditions.

For conditions 3 and 4, scan the generated reasoning trace for the first
released-Qwen3 `Wait` checkpoint in each token interval
`[1024, 2047]`, `[2048, 3071]`, ..., `[7168, 8191]`. A bin with no eligible
`Wait` checkpoint has no trial. This schedule is fixed, applies identically to
both signals, and is saved as actual token positions. It does not change the
released CoDE-Stop baseline in condition 2.

At each scheduled checkpoint, use the same forced-answer suffix and a nested
outer-box parser. The malformed/no-close cap, direct-evaluability policy, and
answer evaluator must be frozen before inference. The candidate cap is 64
generated tokens for malformed/no-close cases. Use `math-verify==0.9.0` through
a versioned wrapper whose source hash and fixtures are recorded before model
calls. A candidate is valid only when its matching outer box closes under that
parser.

For BAC, include exactly the pre-specified candidate payload token positions
used by the Q7 standard BAC rule and exclude the outer opening and closing
brace. Do not generate a post-box continuation. For `c_full`, retain the
released probe window and termination behavior from the pinned upstream Qwen3
path. The paired conditions therefore differ only in confidence span and
boundary behavior.

## 4. Four compared conditions

| Condition | Frozen behavior |
| --- | --- |
| 1. Full reasoning | No early stopping. Use the normal final-answer path after up to 8,192 reasoning tokens. |
| 2. Released CoDE-Stop | Run the pinned upstream code/configuration and its own released confidence, gates, and stopping semantics without modification. |
| 3. Risk-controlled `c_full` | Use only the Conformal Thinking-style upper threshold and the released full-span confidence signal. |
| 4. Risk-controlled BAC | Use the identical upper-threshold procedure, but terminate each trial at the completed outer box and score BAC. |

Conditions 3 and 4 must hold fixed the data split, checkpoint schedule, prompt
and forced suffix, greedy semantics, candidate parser, answer evaluator,
maximum reasoning budget, risk loss, `epsilon`, `delta`, threshold grid, and
tie-break. No CoDE-Stop degeneration score, ramp, or eligibility gate is added
to only one of these two new comparison conditions.

## 5. Risk-control procedure

The controller is the upper-threshold component of
[Conformal Thinking](https://arxiv.org/html/2602.03814v2), not a replacement
interval or a newly named heuristic. For each signal `s` and threshold
`lambda`, an example exits at its first checkpoint satisfying `s >= lambda`.

The primary controlled loss is the paper’s upper loss:

```text
loss_i_plus(lambda) = 1[example i exits early at the upper threshold]
                      * 1[candidate at that exit is incorrect]
R_hat_plus(lambda) = mean_i loss_i_plus(lambda)
```

This is an unconditional wrong-early-exit rate. Also report the descriptive
stopped-case error, `wrong early stops / all early stops`, separately and mark
it undefined when no example stops early.

For every signal, use the same fixed grid:

```text
Lambda = {0.000, 0.005, 0.010, ..., 0.995, 1.000}
epsilon = {0.05, 0.10}
delta = 0.10
```

For each `lambda`, compute the published pointwise Hoeffding UCB:

```text
R_UCB_plus(lambda) = R_hat_plus(lambda) + sqrt(log(1 / delta) / (2 * n))
```

with `n = 20`. Retain only `lambda` values with
`R_UCB_plus(lambda) <= epsilon`. Among feasible values, choose the minimum of
the paper’s upper-threshold efficiency loss `J_plus` using the definition in
the paper; ties use the smallest numerical `lambda`. Record the complete UCB
and selection table before touching the test set. The simple pointwise
correction is used as reported by the paper; no post-hoc simultaneous-grid
correction or alternative interval will be substituted.

The risk-monotonicity condition required by the paper must be checked and
reported for each signal/grid. If it fails, do not claim the UCB guarantee or
repair the procedure after seeing calibration outputs.

## 6. Predeclared feasibility and abort gates

The 20-example calibration design has a material finite-sample boundary. With
`delta = 0.10`, the UCB correction is approximately `0.2399`, so even a zero
empirical loss cannot satisfy `epsilon = 0.05` or `0.10`. Under this frozen
configuration, no deployable threshold can be UCB-feasible at either target.

This is not a reason to silently relax the target, change `delta`, change the
split, or replace the interval. It is a predefined **underpowered / no
deployable UCB threshold** outcome. The study must stop before any test-set
model output is generated. The test evaluation plan below remains frozen for
auditability; it cannot be entered unless a future protocol is explicitly
replaced before any inference.

Independently of that known feasibility limit, stop before test inference if:

- calibration lacks both correct and incorrect directly evaluable checkpoint
  candidates, or lacks an evaluable potential upper exit;
- malformed or unscorable candidates prevent construction of the frozen loss
  table;
- no threshold is UCB-feasible for either signal and risk target;
- the required risk-monotonicity condition fails; or
- model, runtime, prompt, tokenizer, parser, or provenance differs from the
  frozen manifest.

On any abort, preserve calibration artifacts and report the outcome. Do not add
examples, change the split, alter `epsilon` or `delta`, tune the grid, change
the method, or introduce another signal. The 40-example test set remains
untouched.

## 7. Official-code decision

The official Conformal Thinking repository,
[`xidulu/reasoning_risk_control`](https://github.com/xidulu/reasoning_risk_control),
was inspected at HEAD `6551e3000dcda3d76491f30cc687d64618807c5b`. It is
described by its authors as preliminary and is not a complete documented
end-to-end implementation for this instrumentation. No code from it is
vendored here.

If a future study is explicitly authorized, the cleaner approach is a small,
independent upper-only implementation directly from the cited paper’s
definitions and UCB formula, with numeric unit fixtures for the published
formula and a recorded source hash. It must be labeled an upper-only
application, not Conformal Thinking’s full dual-threshold method.

## 8. Frozen reporting requirements if a future protocol reaches test

For every condition and operating point, report:

- final-answer accuracy, numerator, and denominator;
- primary wrong-early-exit risk and descriptive stopped-case error;
- average reasoning tokens;
- trial-probe generated tokens;
- total generated tokens including probe overhead;
- percentage stopped early;
- stopping checkpoint and token index;
- calibration-selected threshold and its complete UCB table;
- candidate correctness at stopping; and
- malformed and non-evaluable counts.

For BAC, additionally report the **actual matched trial-probe token savings**:
released `c_full` trial tokens minus real boundary-stopped BAC trial tokens at
the same scheduled probes. Do not relabel this as total-inference saving. No
threshold may be selected using the test set.

## 9. Interpretation rule

The final contribution depends on a future study satisfying this protocol and
its feasibility gates. Until then, the established contribution is the
measurement audit and Q7 precision evidence, not a validated early-stopping
method.
