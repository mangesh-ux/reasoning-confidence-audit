# Methodology

## Completed Q0–Q7 audit

The completed work is a frozen reproduction/audit sequence. Q3 supplied a
deterministic development batch; Q4 and Q5 analyzed those frozen traces; Q6
used an independent preregistered holdout selected before its model execution;
and Q7 measured precision fidelity with fixed tokenized reasoning prefixes.
CoDE-Stop was not modified during the audit.

The historical sandbox used `Qwen/Qwen3-4B` at revision
`1cfa9a7208912126459214e8b04321603b3df60c` and llama.cpp commit
`7798007a29a90e3053e799394da48cf53a2f8e0f`. Q4_K_M was the original
exploration backend. It is not presented as a faithful BF16 reproduction.

### Measurement comparison

For a frozen prompt and reasoning prefix, the audit compares:

- **Released full-span confidence (`c_full`):** the released probe’s
  probability-based measurement over its configured generated span.
- **Boundary-Aligned Confidence (BAC):**

  `BAC = exp(mean(log(q_j)))`

  over the pre-specified generated candidate-answer tokens. The candidate ends
  at the matching outer `\boxed{...}` close, and post-box tokens are excluded.

The boundary calculation is a measurement audit. It was not substituted into
the released CoDE-Stop decision rule in Q0–Q7.

### Holdout accounting

Q6 preserved the released inference behavior and performed offline boundary
accounting. Its token comparison is explicitly counterfactual: it asks how
many trial-probe tokens would not have been generated if an already-completed
candidate box had ended the probe. It does not measure total end-to-end
inference savings or accuracy improvement.

### Q7 precision-fidelity design

Q7 froze 30 primary checkpoints spanning Q3 development and Q6 holdout
trajectories, including early, middle, and late positions. A deterministic
12-checkpoint subset was defined for BF16 before Q7 candidate generation.
Every paired probe reused the same base-prompt token IDs, reasoning-prefix
token IDs, forced suffix token IDs, greedy semantics, and candidate-boundary
parser.

The comparison used local Q8_0 generated from the exact local BF16 GGUF and
left the existing Q4_K_M artifact unchanged. Q7 reports candidate agreement,
BAC differences/correlations, threshold agreement at fixed audit thresholds,
and malformed output explicitly. TQ1_0 was treated only as an extreme
post-training ternary stress condition, not as a trained ternary model.

## Public aggregate packaging

The repository contains compact aggregate JSON only. The standard-library
[result packager](../src/rebuild_public_results.py) reads aggregate inputs,
validates their structure, and writes a public summary. It is not a model
runner and does not start a server, generate tokens, tune thresholds, or alter
frozen artifacts.

## Next study

The proposed risk-controlled study is intentionally separate from the completed
audit. Its pre-specified data split, runtime, loss, UCB procedure, abort rules,
and reporting requirements are in
[next_study_protocol.md](next_study_protocol.md). It has not been executed.
