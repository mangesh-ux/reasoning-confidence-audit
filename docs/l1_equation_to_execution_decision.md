# L1 — Equation-to-Execution Logical Audit: Decision Record

## Terminal classification

**FORMAL SEMANTIC DISTINCTNESS CONFIRMED — NON-EMPIRICAL ONLY.**

L1 confirms that several version-pinned released CoDE-Stop expressions are
formally distinct from natural readings of the paper's displayed equations.
It does not establish an empirical effect, a better equation, a better
stopping policy, calibration, accuracy, token savings, runtime behavior, or
publication-level novelty by itself.

The frozen protocol is [here](l1_equation_to_execution_protocol.md). No model,
dataset, tokenizer, completion, trace, frozen-study output, network request,
or GPU process was used.

## Verification record

| Check | Result |
| --- | --- |
| Source provenance | The pinned upstream file `method_codestop.py` matched commit `b5081e7c2abe23bb1d19649421cc13522fee7c50` and SHA-256 `3fca63a96d8caddd7fc46d70939bedc5d6d3455b2993abd72300d4ef4e8519b3`. |
| Paper provenance | The audit used arXiv:2604.04930v2, whose local PDF SHA-256 was `c21cf8affd9cf60cbba6c8065d95786ba59bf0811bc8885076a62700d49c0c14`. |
| Isolation | The new harness is standard-library-only and does not import or execute upstream code. |
| Test command | `PYTHONPATH=src python -B -m unittest discover -s tests -v` from the public-release root. |
| Predeclared L1 fixtures | **18/18** passed. |
| Full public synthetic suite | **34/34** passed: 15 pre-existing audit tests, 18 predeclared L1 tests, and one source-fidelity regression described below. |

The protocol's link to the current upstream `master` branch is a literature
discovery reference only. Every semantic statement in this record is tied to
the pinned commit and file hash above, not to a later upstream revision.

## Confirmed formal results

### 1. Default degeneration semantics are a strict-drop count

For \(m \ge 3\) checks, let
\(\ell_i = \log(\max(c_i,10^{-12}))\). The released default computes:

\[
D_m = \sum_{i=2}^{m}
\mathbf{1}[\ell_{i-1}>\ell_i]\,
\mathbf{1}[2\ell_i-\ell_{i-1}<0.55]
\left(\log\frac{T_m}{T_i}+1\right).
\]

For valid confidence values in \((0,1]\), a strict decrease in the
floor-clamped log values implies \(\ell_{i-1}>\ell_i\) and
\(\ell_i\le0\). Therefore \(2\ell_i-\ell_{i-1}<\ell_i\le0<0.55\): the
inner log-domain indicator is automatically true after the strict-drop gate.
On that domain, the released default reduces exactly to:

\[
D_m = \sum_{i=2}^{m}
\mathbf{1}[\ell_{i-1}>\ell_i]
\left(\log\frac{T_m}{T_i}+1\right),
\]

with the separate method-level rule that sets \(D=0\) before the third check.
It is therefore a recency-weighted count of strict drops in the floor-clamped
log confidence, rather than an independently active log-space instability
test. When both adjacent raw confidence values are at least \(10^{-12}\), this
is equivalently a strict raw-confidence drop; values below the floor can tie
after clamping and are not overclaimed as raw drops.

During final source-fidelity review, an explicit tiny-confidence regression
`(1e-13, 1e-14, 1e-15)` was added to verify this floor behavior. It evaluates
to zero because all three values clamp to `1e-12`. This is a transparent
post-freeze source-fidelity guard, not a new L1 comparison fixture or an
outcome used to select an equation.

The synthetic fixture `(0.9, 0.8, 0.7)` at offsets `(10, 20, 30)` yielded
`log(1.5) + 2` for the released reconstruction and `0` for raw-domain Eq. 3
with the same strict-drop gate. This is a semantic contrast, not a performance
comparison.

### 2. The strict-drop gate changes the represented events

The displayed raw Eq. 3 condition can fire on small improvements and equal
confidence values. In the frozen fixtures `(0.4, 0.45, 0.46)` and
`(0.4, 0.4, 0.4)`, the ungated raw comparison produced `log(1.5) + 2`, while
the released strict-drop reconstruction produced `0`. Thus the gate is not a
cosmetic implementation detail.

### 3. Other exact, limited semantic differences

- The ramp uses zero-based checkpoint indices; a one-based coordinate reading
  changes early thresholds in the predeclared `0.90`–`0.95` example.
- The displayed temporal weight and the released `log1p(T_k/T_i - 1) + 1`
  expression are algebraically identical for positive offsets. L1 found no
  Eq. 4 discrepancy and did not invent an alternate weight.
- The released stop rule uses strict `>` comparisons and separately gates the
  confidence branch on terminal eligibility. The inclusive/ungated comparison
  differs at equality and terminal-ineligible fixtures; the degeneration branch
  itself remains ungated.
- The released forced-answer normal-path score excludes the first and final
  selected tokens while retaining denominator \(n-1\), and the generation cap
  is 21 selected tokens. The two-token edge reconstructs to `1.0` in the
  geometric branch and `0.0` in the arithmetic branch; the one-token formula
  has no valid denominator and was left undefined.

## What this changes—and what it does not

L1 strengthens the reproducibility/measurement-audit manuscript: it supplies
a version-pinned, independently executable bridge from source-level claims to
hand-derived fixtures. It supports writing that the *released default* has the
semantics above.

It does **not** support calling a raw-domain indicator, a different gate, a
uniform weight, a new delta, or a shifted threshold an improved CoDE-Stop
plug-in. CoDE-Stop's own paper already studies alternate degeneration
functions and weights; L1 did not compare outcomes from them. Nor does L1
change M1's completed result or M2's terminal runtime-infeasibility outcome.

## Next decision

The recommended next substantive deliverable is a manuscript-quality
reproducibility package built around: (1) the source-to-equation audit,
(2) L1's executable formal checks, (3) the completed M1 measurement result,
and (4) a transparent M2 runtime-abort record. No additional model inference
is authorized by this decision.

An empirical equation ablation would require a separate user authorization and
new pre-inference protocol. It must first qualify the runtime on a
non-benchmark synthetic soak/recovery test, pin the source revision anew, use
a fresh deterministic cohort that does not reuse M1 or all of M2's selected
rows, and pass a new prior-work gate. It must preserve negative results and
may not call a changed equation a new method without independent novelty and
performance evidence.
