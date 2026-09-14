# L1 — Equation-to-Execution Logical Audit

## Status

**Frozen before implementation; no-model audit.** This is a source-level and
synthetic-fixture study authorized after M2's terminal runtime-feasibility
abort. It is not M1, M2, M3, P1, a benchmark study, or a new CoDE-Stop
implementation. It cannot repair, rerun, reinterpret, or pool any frozen
Q0–Q7, M1, or M2 artifact.

The purpose is narrow: establish which apparent paper-to-code distinctions are
algebraically real in the pinned released forced-answer path, and which are
not. A positive result means only that the formal expressions differ on the
predeclared synthetic inputs. It is not evidence that a replacement equation
improves stopping, calibration, accuracy, cost, or safety.

## Pinned sources

| Source | Pin |
| --- | --- |
| CoDE-Stop implementation | commit [`b5081e7c2abe23bb1d19649421cc13522fee7c50`](https://github.com/sudoparsa/CoDE-Stop/tree/b5081e7c2abe23bb1d19649421cc13522fee7c50) |
| Audited file | `method_codestop.py`, SHA-256 `3fca63a96d8caddd7fc46d70939bedc5d6d3455b2993abd72300d4ef4e8519b3` |
| Paper | [arXiv:2604.04930v2](https://arxiv.org/html/2604.04930v2), PDF SHA-256 `c21cf8affd9cf60cbba6c8065d95786ba59bf0811bc8885076a62700d49c0c14` |

The local upstream checkout has unrelated dirty files. The audited file above
was verified clean against its pinned commit. The audit reimplements only the
specified arithmetic in a standard-library test harness; it does not import,
modify, distribute, or execute upstream CoDE-Stop code.

## Prohibited inputs and outputs

L1 uses only hand-written numeric sequences and booleans. It must not read or
generate a model completion, benchmark row, reasoning trace, tokenizer output,
chosen-token log-probability trace, server log, M1/M2 output, or frozen-study
result. It must not start a model, server, GPU process, dataset download, or
network request.

No parameter is tuned against an empirical outcome. In particular, L1 does
not change `delta`, `tau`, a confidence threshold, a ramp range, a decoder,
candidate boundary, a token budget, or a weight function for performance.

## Frozen comparison matrix

Each comparison is an interpretation instrument, not a proposed replacement
method. The implementation will test factors separately; it will not perform
a search over combinations or transfer a threshold between non-equivalent
scores.

| Component | Released reconstruction | Comparison instrument | Predeclared interpretation |
| --- | --- | --- | --- |
| Eq. 1 + Eq. 3 degeneration | log-domain values, strict-drop outer gate, current-horizon weights, and the method's fewer-than-three-check zeroing | raw-domain Eq. 3 with the gate retained; raw-domain Eq. 3 with the gate removed; log-domain/no-gate diagnostic cell | Test whether domain and gate are materially non-equivalent. |
| Eq. 2 ramp | zero-based `enumerate` index | one-based checkpoint-coordinate substitution | Test early-check coordinate sensitivity only. |
| Eq. 4 weight | `log(T_k / T_i) + 1` | algebraic identity check only | No alternative weight is tested: the released expression is algebraically the displayed equation for positive offsets. |
| Stop relation | strict `>` comparisons and a separately represented terminal-eligibility gate on the confidence branch | inclusive `>=` comparator; removal of terminal gate, each isolated | Test Boolean semantic differences only. |
| Forced-answer score/cap | first/last-token exclusions, denominator `n - 1`, token-ID terminal membership, and 21 selected-token cap | faithful reconstruction fixtures only | No arithmetic-mean or candidate-boundary replacement is treated as paper-faithful here. |

The paper does not supply a complete executable initialization convention for
the first degeneration term. Consequently, an alternate warm-up is not a
paper correction and is excluded from the matrix.

## Predeclared synthetic fixtures and expected results

All probabilities are artificial values in `(0, 1]`; all offsets are positive
and strictly increasing. Expected results are hand-derived before the test
harness is written.

1. **Score reconstruction.** For selected-token probabilities
   `(0.9, 0.8, 0.7, 0.6)`, the released geometric branch equals
   `exp((log(0.8) + log(0.7)) / 3)` and the arithmetic branch equals
   `(0.8 + 0.7) / 3`. For two selected tokens, the released normal-path
   formulas evaluate to `1.0` and `0.0`, respectively; one selected token has
   no defined denominator and is recorded as invalid rather than repaired.
2. **Cap and terminal membership.** The cap condition becomes true at 21
   selected tokens, not 20. Terminal completion is membership of the final
   token ID in the configured terminal-ID set, not a decoded-string assertion.
3. **Log-domain redundancy under a strict drop.** With confidences
   `(0.9, 0.8, 0.7)` and offsets `(10, 20, 30)`, the released default score is
   `log(1.5) + 2`; the raw-domain, strict-drop comparison score is `0`.
4. **Added strict-drop gate.** With confidences `(0.4, 0.45, 0.46)` and the
   same offsets, raw Eq. 3 without the gate is `log(1.5) + 2`, while all
   strict-drop variants are `0`.
5. **Equal-confidence edge.** With `(0.4, 0.4, 0.4)`, the ungated raw
   comparison is `log(1.5) + 2`; strict-drop variants are `0`.
6. **Warm-up.** With two decreasing checks, the released *method* score is
   `0` because its caller overwrites the helper result before the third check.
7. **Horizon recomputation.** At current offset `30`, the weight of offset
   `20` is `log(30 / 20) + 1`; at current offset `60`, it is
   `log(60 / 20) + 1`.
8. **Ramp coordinate.** For `r_min=0.90`, `r_max=0.95`, and `steps=2`, the
   released checkpoints are `(0.90, 0.925, 0.95)`; the one-based substitution
   is `(0.925, 0.95, 0.95)`.
9. **Comparator boundaries and terminal gate.** At `c=r` or `D=tau`, the
   released strict rule does not stop and the inclusive comparison does. A
   terminal-ineligible confidence above the threshold does not trigger the
   released gated confidence branch, while a degeneration score above `tau`
   remains eligible independently of that gate.

## Planned implementation and decision rule

The public-safe implementation consists solely of a standard-library module
and `unittest` fixtures. The test command is:

```powershell
$env:PYTHONPATH = "src"
python -B -m unittest discover -s tests -v
```

If every expected synthetic result holds, L1 will establish a formal
equation-to-execution sensitivity finding suitable for the reproducibility
section of the measurement-audit manuscript. It will **not** authorize model
inference or an equation update. A later empirical comparison would require a
separate user authorization, fresh protocol, new non-overlapping cohort,
runtime qualification, source-version check, and a new literature gate.

If a synthetic expectation fails, the mismatch will be preserved and the
source-level description corrected; no empirical expansion follows.

## Literature gate

A bounded primary-source check found no public work that performs this exact
paper-equation-to-released-code audit for CoDE-Stop's forced-answer scorer and
stop semantics. CoDE-Stop itself does ablate alternate degeneration functions
and weights, so L1 makes no claim that an altered function is a new or better
plug-in. The related forced-answer and risk-control papers are not used as
evidence of implementation equivalence. See the [CoDE-Stop paper](https://arxiv.org/html/2604.04930),
[official implementation](https://github.com/sudoparsa/CoDE-Stop/blob/master/method_codestop.py),
[Conformal Thinking](https://arxiv.org/html/2602.03814v2), and
[REFRAIN](https://aclanthology.org/2026.acl-long.1256/).

This bounded search cannot establish global absence of overlap. Any newly
released direct audit supersedes this protocol's novelty assessment.
