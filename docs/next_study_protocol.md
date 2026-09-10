# Next-study protocol: Boundary-Aligned Confidence under Risk-Controlled Early Stopping

**Status: corrected, frozen pre-inference protocol. This study has not been run.**

## 1. Research question and boundary

This is one bounded practical local study, not an exact 32K-token reproduction
of an upstream paper:

> Does Boundary-Aligned Confidence (BAC), under the same upper-risk controller,
> provide a better accuracy, risk, and compute trade-off than the released
> full-span confidence measurement?

The protocol keeps BAC fixed: the geometric mean of the pre-specified
candidate-answer token probabilities, stopping the probe at the matching outer
`\boxed{...}` close. It introduces no lower/unsolvable threshold, semantic
redundancy, PUMA, CUSUM, ternary condition, or additional stopping signal.

## 2. Frozen model, benchmark, and split

| Item | Pre-specified choice |
| --- | --- |
| Primary model | Qwen3-4B `Q8_0` |
| Q8_0 SHA-256 | `0d5964f2837d157bf8d845f09b006254b85389ef4293ec0f41dd8ffeab1ab3f0` |
| BF16 role | Small predefined fidelity anchor only; never used for threshold selection or primary claims |
| BF16 anchor | Eight examples: four calibration and four test, selected deterministically |
| Q4_K_M role | Historical exploratory evidence only; not a primary validation model |
| Benchmark | MATH500 test split |
| Primary study size | 200 examples: 100 calibration and 100 untouched test |
| Maximum reasoning budget | 8,192 generated reasoning tokens per problem |
| Runtime source | llama.cpp `7798007a29a90e3053e799394da48cf53a2f8e0f` |

Before **any** model call, pin and record the exact MATH500 dataset revision,
source URL, license information, schema, and dataset fingerprint or content
SHA-256. The planned universe is all 500 rows in that pinned test split. A
schema mismatch or row-count mismatch is an abort condition; it must not be
fixed by filtering rows after inspection.

For each row, create a non-public selection key from the dataset revision,
source row index, and SHA-256 of normalized problem text. Rank all 500 rows by:

```text
SHA256("BAC_RC_MATH500_SELECTION_V2|<dataset-revision>|<row-index>|<problem-sha256>")
```

Take the first 200. Independently rank only those 200 rows by:

```text
SHA256("BAC_RC_MATH500_SPLIT_V2|<dataset-revision>|<row-index>|<problem-sha256>")
```

Assign the first 100 to calibration and the remaining 100 to untouched test.
Dataset identity, row index, and problem-text hash are the only selection and
split inputs. Reference answers, categories, model outputs, correctness, and
confidence must not affect either operation. Write and SHA-256 a manifest with
row keys, problem hashes, selection salts, split labels, and source provenance
before inference. Do not publish raw problem text or benchmark rows.

For the BF16 anchor, independently rank calibration and test rows by:

```text
SHA256("BAC_RC_MATH500_BF16_V2|<dataset-revision>|<row-index>|<problem-sha256>")
```

Take four from each split. Freeze its manifest before inference. BF16 results
are fidelity diagnostics only and never influence threshold selection, model
choice, or primary accuracy/risk reporting.

## 3. Frozen runtime and probe semantics

Before execution, record model and binary SHA-256 values, GPU/CPU placement,
driver version, tokenizer/model revision, context size, prompt template, seed,
temperature, top-p, top-k, and all remaining decoding settings. The runner
must reuse exact base-prompt token IDs, reasoning-prefix token IDs, and
forced-suffix token IDs for paired probes. It must not rerender a chat template
between conditions.

Before any model output, write and hash one versioned execution manifest that
freezes the threshold grid, tie-break, checkpoint schedule, forced suffix,
parser version, evaluator version, malformed-candidate policy, candidate cap,
and all decoding settings. A change to any of these items is a provenance
failure, not a reason to revise the protocol after seeing results.

The shared checkpoint schedule for conditions 3 and 4 is fixed as follows:
scan for the first released-style `Wait` token-ID membership checkpoint in each
reasoning-token interval `[1024, 2047]`, `[2048, 3071]`, ...,
`[7168, 8191]`. A bin without an eligible checkpoint has no trial. Save the
actual checkpoint token positions. This is an upstream-specific membership
rule, not a universal checkpoint detector, and it does not modify condition 2.

At every scheduled checkpoint, use the same forced-answer suffix, greedy
one-token generation, outer-box parser, candidate cap, malformed-candidate
policy, and versioned answer evaluator. The candidate cap is 64 generated
tokens for malformed/no-close cases. The parser must record nested braces and
whether a closing token contains trailing characters. A candidate is usable
only when its matching outer box closes and the predeclared evaluator can score
it.

For BAC, include exactly the Q7 positions strictly between the opening-brace
token and outer-closing-brace token. Do not generate post-box continuation. For
`c_full`, use the same prefix, suffix, greedy settings, cap, parser, and
malformed policy, but retain the released full-span measurement window: a
completed box does not terminate the trial, and generated post-box positions
remain eligible for the released reconstruction through the frozen cap or a
normal terminal token. The boundary and confidence span are the only intended
differences between conditions 3 and 4.

## 4. Four conditions

| Condition | Frozen behavior |
| --- | --- |
| 1. Full reasoning | No early stopping. Use the normal final-answer path after up to 8,192 reasoning tokens. |
| 2. Released CoDE-Stop | Run the pinned upstream code/configuration and its own released confidence, gates, and stopping semantics without modification. |
| 3. Risk-controlled released `c_full` | Use the upper-risk controller with the released full-span probe and confidence signal. |
| 4. Risk-controlled BAC | Use the same upper-risk controller, but stop each probe at the completed outer box and score BAC. |

Conditions 3 and 4 must share the examples, calibration/test split, checkpoint
schedule, answer forcing, greedy decoding, parser, evaluator, malformed policy,
reasoning budget, upper loss, `epsilon`, `delta`, threshold grid, and tie-break.
No degeneration mechanism, ramp, or other gate may be added to only one of
them.

## 5. Upper-risk control

The controller uses only the upper-threshold component motivated by
[Conformal Thinking](https://arxiv.org/html/2602.03814v2). For signal `s` and
threshold `lambda`, an example exits at its first eligible checkpoint with
`s >= lambda`.

The primary controlled loss is the published upper wrong-early-exit loss:

```text
loss_i_plus(lambda) = 1[example i exits early at the upper threshold]
                      * 1[candidate at that exit is incorrect]
R_hat_plus(lambda) = mean_i loss_i_plus(lambda)
```

This is an unconditional wrong-early-exit rate. Report error among stopped
examples separately as a descriptive quantity; it is undefined when no
examples stop early.

For both signals, predeclare the same grid and selection rule:

```text
Lambda = {0.000, 0.005, 0.010, ..., 0.995, 1.000}
epsilon = {0.15, 0.20}
delta = 0.10
```

With `n = 100`, use the published pointwise Hoeffding UCB:

```text
R_UCB_plus(lambda) = R_hat_plus(lambda) + sqrt(log(1 / delta) / (2 * n))
```

The correction is `sqrt(log(10) / 200) ≈ 0.1073`. Therefore `epsilon = 0.15`
permits empirical wrong-early-exit risk no larger than about `0.0427` (at most
4 losses in 100), and `epsilon = 0.20` permits no larger than about `0.0927`
(at most 9 losses in 100). These operating points are fixed before any MATH500
inference. `epsilon = 0.05` and `0.10` are not primary operating points because
100 calibration examples cannot certify `0.10` even at zero empirical loss.

Among thresholds with `R_UCB_plus(lambda) <= epsilon`, select the smallest mean
published upper efficiency loss:

```text
J_i_plus(tau_i) = max(0, tau_i - t_prime_i) / T
```

where `tau_i` is the selected exit location, `t_prime_i` is the first correct
checkpoint for example `i`, and `T` is the maximum reasoning budget. Ties use
the smallest numerical `lambda`. Freeze the complete UCB, feasibility, and
selection table before test inference.

For this upper-only, checkpointed operationalization, define `tau_i = T` when
no eligible checkpoint reaches `lambda`, and define `t_prime_i = T` when no
eligible checkpoint has a directly evaluable correct candidate by the budget.
This makes the published first-correct-step efficiency expression executable
for a no-exit or never-correct trajectory: it assigns no post-correct-token
regret where no earlier correct checkpoint exists. This convention affects only
the secondary efficiency selection among UCB-feasible thresholds, never the
wrong-early-exit UCB loss. Freeze a synthetic fixture for it with the runner;
if a pinned future reference implementation specifies a conflicting convention,
abort rather than silently substitute a different procedure.

The simple correction is pointwise while scanning the grid, as described in
the paper. It is not presented as a blanket simultaneous-grid guarantee. Check
and report the method’s required risk-monotonicity condition for each
signal/grid; if it fails, do not claim the UCB guarantee.

## 6. Pre-test gates and abort conditions

Run calibration only until it selects a threshold or triggers an abort. Do not
inspect or generate any primary test-set output first. Abort before test
inference if any of the following occurs:

- calibration lacks both correct and incorrect directly evaluable checkpoint
  candidates, or lacks an evaluable potential upper exit;
- no threshold is UCB-feasible for a signal and operating point;
- required risk monotonicity fails;
- candidate parsing or evaluation is not sufficiently defined;
- malformed or unscorable candidates prevent construction of the frozen loss
  table; or
- dataset, model, runtime, prompt, tokenizer, parser, evaluator, or binary
  provenance differs from the frozen manifest.

On abort, preserve calibration artifacts and report the negative or
underpowered outcome. Do not change the split, add examples, alter `epsilon` or
`delta`, tune the grid, repair the protocol from test data, or introduce
another signal.

## 7. Official-code boundary

The official Conformal Thinking repository,
[`xidulu/reasoning_risk_control`](https://github.com/xidulu/reasoning_risk_control),
was inspected at HEAD `6551e3000dcda3d76491f30cc687d64618807c5b`. It is
preliminary and is not bundled or copied here. If future execution is
authorized, implement only the small upper-only calculation from the cited
paper with versioned numeric fixtures. Label it as an upper-only application,
not a reproduction of the paper’s full dual-threshold method.

## 8. Reporting plan if test evaluation is reached

For every condition and operating point, report:

- final-answer accuracy;
- primary wrong-early-exit risk;
- error among stopped examples;
- average reasoning tokens;
- trial-probe generated tokens;
- total generated tokens including probe overhead;
- fraction stopped early;
- stopping checkpoint and token index;
- calibration-selected threshold and complete UCB table;
- candidate correctness at stopping; and
- malformed and non-evaluable counts.

For BAC, report actual boundary-stopped probe generation, not a counterfactual.
The primary publication decision is: at controlled early-stop risk, does BAC
reduce total generated-token cost relative to risk-controlled `c_full`?

## 9. Interpretation rule

The completed Q0–Q7 work establishes an audit finding and limited
precision-fidelity evidence. This protocol does not establish a new stopping
method. If BAC does not improve the paired risk-compute trade-off, preserve the
negative result and do not invent another stopping signal within this project.

The feasibility correction that replaced the original 20-example design is
documented in [protocol_feasibility.md](protocol_feasibility.md).
