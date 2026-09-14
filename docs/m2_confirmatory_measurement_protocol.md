# M2 Confirmatory Forced-Answer Measurement Audit

> **Release status (2026-09-14):** The content below is M2's frozen
> pre-inference protocol. M2 later stopped as **EFFECT NOT CONFIRMED — runtime
> infeasible**; it produced 18 primary-valid pairs rather than the required 80
> and did not start the BF16 anchor. See the
> [runtime-feasibility abort record](m2_runtime_feasibility_abort.md). This
> status note is not part of the frozen protocol body.

## Status, authority, and scope

M2 is a new confirmatory measurement and reproducibility study authorized on
2026-09-13. M1 is complete and frozen. M2 does not modify, rerun, repair, or
reinterpret any M1 artifact, and M1 outcomes are not pooled with M2 outcomes.

The primary question is:

> On a new non-output-selected MATH-500 sample, does the pinned CoDE-Stop
> released forced-answer implementation materially differ from an exact
> candidate-boundary interpretation in measured confidence, illustrative
> stopping decisions, and forced-probe generation work?

M2 is not a new confidence metric, early-stopping algorithm, threshold-safety
study, generic BAC novelty claim, or end-to-end reasoning-savings study. P1
remains paused and no risk controller, calibration split, test split, or
threshold selection from P1 is used here. M3 is not authorized by this
protocol; a positive M2 terminal decision is only a gate for designing a
separate M3 protocol.

## Frozen cohort and provenance

The cohort is exactly 100 MATH-500 test examples. It uses the source
repository HuggingFaceH4/MATH-500, revision
2343f79f3640c0f795bbf4e3234396cfe9266d0f, and source file test.jsonl.
Selection is deterministic before any M2 model completion:

1. Normalize each problem with Unicode NFC and LF line endings.
2. Exclude every M1 row through the frozen M1 private-manifest SHA-256
   f8993979491579391fae2e8f6f2e1e2f4de6d62dc37f403141fc8220c65a7e43.
3. Exclude a conservative P1-shadow universe, derived read-only from the
   unexecuted P1 protocol's selector using this M2 source revision and explicit
   normalization. This protects a possible future P1 cohort without claiming
   that P1 itself has a materialized or frozen sample.
4. Rank remaining identities by SHA-256 of the M2 namespace, source revision,
   zero-based row index, and normalized-problem SHA-256.
5. Retain the first 100 rows, with no replacements for short, malformed,
   failed, or single-class observations.

The private manifest contains source-row identities, answers, prompt token IDs,
and row hashes only in the ignored private workspace. The committed public
digest contains source, algorithm, aggregate selection fingerprints, and
zero-overlap assertions, but no benchmark text, answers, token sequences, or
row identifiers.

Before a completion request, M2 freezes and hashes the private manifest,
public-safe manifest digest, code bundle, synthetic-test result, dataset,
model, tokenizer assets, runtime binary and companion libraries, prompt,
decoder, parser, score definitions, checkpoints, thresholds, evaluator, and
analysis source. Each immutable record uses exclusive creation; an intent with
no outcome is terminal and is never retried.

P1 has no materialized selection manifest because it is paused before
inference. The M2 shadow selector is therefore not P1 data and does not modify
P1. It is a conservative exclusion of the first 200 identities ranked by
SHA-256 of BAC_RC_MATH500_SELECTION_V2, the M2 source revision, zero-based row
index, and M2's explicitly normalized problem hash. The manifest records the
P1 protocol file SHA-256 4d90acdd486a17d3597c8caead0f1e46e4c0c247003802475d867e73f492c89b,
the shadow-selector fingerprint, and its aggregate overlap count only.

## Fixed runtime and probe coordinate

The primary backend is the pinned Qwen3-4B Q8_0 artifact and the same
llama.cpp runtime family used by M1:

| Item | Fixed value |
| --- | --- |
| Model | Qwen3-4B revision 1cfa9a7, Q8_0 |
| Q8_0 SHA-256 | 0d5964f2837d157bf8d845f09b006254b85389ef4293ec0f41dd8ffeab1ab3f0 |
| Tokenizer revision | 1cfa9a7208912126459214e8b04321603b3df60c |
| llama.cpp source revision | 7798007a29a90e3053e799394da48cf53a2f8e0f |
| Context | 4096 tokens |
| Base decode | M1-pinned sampled base decode, 2048-token maximum |
| Release-coordinate checkpoints | 512, 1024, 1536 |
| Forced cue | newline, bold Final Answer, two newlines, then The final answer is boxed |
| Probe decode | greedy, one selected token per request |
| Probe maximum | 21 selected tokens |

The manifest pins the exact tokenizer IDs of the cue and released terminal
string. Base trajectories retain native generated IDs, decode with skip-special-tokens enabled, and are
retokenized in the same release coordinate as M1. A checkpoint is available
only when that fixed coordinate reaches it. The Q8_0 and BF16 runtimes must
both pass load-only preflight before any model completion. Preflight does not
issue a completion request.

## Conditions and shared-trace accounting

For each available M2 row/checkpoint, one greedy trace is generated from the
same Q8 release-coordinate prefix and forced cue.

### A. Released semantics

A ends at the first selected token whose ID belongs to the pinned tokenizer
encoding of the released terminal string, or at selected token 21. Its score
is the exact released reconstruction:

~~~text
c_full = exp(sum(log q_j for j = 2,...,n-1) / (n - 1))
~~~

where n is the selected-token endpoint count. The first and last selected
tokens are excluded from the numerator while the denominator remains n - 1.
An undefined or non-finite score is missing, never repaired.

### B. Exact candidate boundary

B has the same input, cue, greedy path, and 21-token cap. It ends immediately
after the token containing the matching outer closing brace of the forced
boxed answer. The parser requires the first character of the first nonempty
selected token to be an opening brace, tracks nested braces character by
character across pieces, treats escaped braces as structural, and records
malformed/no-close states rather than inventing a boundary.

Let \`o\` and \`c\` be the zero-based selected-token indices of the token
containing the outer opening brace and the token containing its matching outer
closing brace, respectively.  B excludes both brace-containing pieces, even
when the opening brace appears after one or more empty decoded pieces:

~~~text
boundary_score = exp(mean(log q_i for i = o+1,...,c-1))
~~~

The score is undefined when that interior token set is empty or has a
non-finite chosen log-probability. This score is a comparison instrument, not
a proposed score or controller. M2 also records
\`c_boundary_release_denominator\`, which applies A's released numerator
convention to B's endpoint prefix: for close index \`c\`, it uses selected
indices \`1,...,c-1\` with denominator \`c\`. It is a diagnostic only.

The shared rollout continues until both A and B endpoints exist or the common
21-token cap is reached. It records A and B policy-prefix selected-token
counts, prefix client request time, and the physically executed shared-trace
count/time. Prefix accounting is not an independently rerun latency result
and cannot be called realized total inference saving.

## Paired validity, outcomes, and missingness

A primary valid pair is one unique row/checkpoint with all of:

1. An available fixed base checkpoint.
2. A completed shared rollout with no unknown-outcome request.
3. A valid matching B outer close at or before A's released endpoint.
4. Exact A/B token-ID and decoded-piece prefix agreement through that close.
5. Normalized candidate agreement through the boundary.
6. Finite c_full and boundary_score under the frozen formulas.

All attempted/base/checkpoint/probe/parser/integrity/score failures remain in
a flow table with exact denominators and reasons. They are not replaced,
silently skipped, or turned into a pair.

Primary confirmatory outcomes are:

A. Fraction of primary valid pairs where A continues after the B close.
B. Distribution of A post-boundary selected-token count.
C. Paired absolute score difference.
D. Fraction of valid pairs with absolute difference at least 0.05.
E. First-crossing disagreement at strict thresholds 0.70, 0.80, 0.90, 0.95.
F. Aggregate B/A policy-prefix token ratio.

First-crossing is illustrative only. An example is eligible when it has at
least two scheduled, available checkpoints and no missing or invalid pair at
an available checkpoint. It counts once if A and B differ at one or more
frozen thresholds, including a crossing by one condition when the other never
crosses. The result is reported per threshold and as the predeclared union.

Secondary descriptive outcomes are score Spearman rank correlation using
average ranks for ties; candidate correctness; AUROC/AUPRC only with both
classes; high-confidence-wrong counts; Brier score and log loss only when
defined; the endpoint-denominator diagnostic; aggregate shared-trace token and
timing fields; and paired percentage endpoint reduction. No secondary result
rescues a failed primary gate.

Candidate correctness is descriptive only. M2 uses math-verify 0.9.0 with
parsing and verification errors retained as non-evaluable, and a fixed
15-second outer worker timeout. It is not the upstream MATH-500 model-graded
evaluator and it cannot rescue a failed paired measurement gate.

## Confirmation criteria

M2 is CONFIRMED only when all conditions below hold using unrounded point
estimates:

1. At least 80 primary valid pairs.
2. At least 50% of those pairs have A continuation after B closes.
3. Median absolute score difference is at least 0.05.
4. At least 20% of eligible examples, and at least 20 eligible examples, have
   a first-crossing disagreement at one or more frozen thresholds.
5. Sum(B policy-prefix tokens) / sum(A policy-prefix tokens) is at most 0.75.

These are confirmatory decision criteria rather than significance tests,
deployment guarantees, or safe thresholds.

## Uncertainty and precision anchor

All paired uncertainty intervals resample examples rather than checkpoints.
M2 uses a clustered nonparametric bootstrap with 2,000 replicates, master seed
20260913, metric-specific SHA-256-derived seeds, and percentile intervals
using the linear quantile convention. A resampled example retains all its
available checkpoints and missingness. The analyzer reports valid and invalid
replicate counts; it does not silently discard single-class, zero-denominator,
or zero-variance replicates. Medians, IQRs, exact denominators, and missingness
are reported alongside intervals.

The BF16 anchor is a separately ranked, predeclared 12-row subset of the M2
cohort at checkpoint 512. It uses the exact Q8 release-coordinate prefix and
cue; it never generates a BF16 base trajectory. Its pinned BF16 model SHA-256
is 89ee1fd110158671b341bf4a8d45bd4859f60ac1ef7252e89233d2492f712814.
Before any completion, BF16 must pass a load-only preflight at the frozen
context and input bound. If it cannot, M2 stops and reports the failed anchor;
it does not substitute another precision or change the configuration.

The anchor describes, without cross-backend generalization claims, post-boundary
continuation, candidate identity through the boundary, and direction/magnitude
consistency of c_full minus boundary_score. Its predeclared adequacy checks are
at least 8 jointly valid pairs; at least 4 and 50% BF16 continuations; BF16
median absolute score difference at least 0.05; score-difference sign agreement
in at least 75% of jointly valid pairs; and candidate identity agreement in at
least 75% and at least 6 jointly valid pairs. A failed or underpowered anchor
is retained as such and prevents a strong cross-precision interpretation.

## Terminal decision and literature gate

The terminal classification is exactly one of:

- CONFIRMATORY EFFECT: all five primary criteria pass and the BF16 anchor has
  status PASS. This permits design—but not automatic execution—of a separate
  M3/generalization protocol and supports measurement-audit manuscript work.
- WEAK/MIXED EFFECT: either all five primary criteria pass but the BF16 anchor
  is not PASS, or at least 80 primary valid pairs exist and exactly two through
  four of the five primary criteria pass. This permits audit-manuscript work
  only and does not authorize M3 inference.
- EFFECT NOT CONFIRMED: every other outcome, including fewer than 80 primary
  valid pairs or zero/one passing primary criterion. Close empirical expansion;
  do not add datasets to seek a positive result.

Before M2 inference and before its terminal decision, the literature watch
rechecks CoDE-Stop updates, REFRAIN, Conformal Thinking, confidence-elicitation
semantics, forced-answer early stopping, and LLM calibration protocol
sensitivity. If a public artifact supplies this exact pinned
released-CoDE-to-candidate-boundary audit, M2 stops and reports the overlap.

This protocol is pre-inference. No M2 model completion has been issued while
this document is prepared.
