# Deterministic answer evaluation

This isolated module implements the pre-inference answer-evaluation contract
for the activation-continuation study. It uses the installed `math-verify`
backend when available and does not use an LLM as a judge.

Before any benchmark inference, record `evaluator_provenance()` in the frozen
study manifest, including the implementation and backend versions. The caller
must use the same frozen evaluator contract for base trajectories and every
forced stop-now answer.

`evaluate_answer(reference, candidate)` returns an immutable
`EvaluationResult`:

- `evaluated` carries an exact `correct=True` or `correct=False` result.
- `not_evaluable_*` carries `correct=None`, including blank inputs, malformed
  `\boxed{...}` syntax, empty symbolic parses, and an unavailable backend.
- `error_*` also carries `correct=None`; backend exceptions and unexpected
  backend return values are never converted into an incorrect label.

The result object contains only status and parser-count metadata, not raw
reference or candidate text. Synthetic unit fixtures cover integers, decimals,
signed values, fractions, algebraic equivalence, LaTeX boxed answers,
percentages, GSM8K `####` formatting, malformed output, and empty output.
They are not benchmark rows.

The module performs a conservative structural check for unclosed `\boxed`
expressions before symbolic parsing. This prevents a permissive parser from
silently salvaging a partial answer. Balanced input is otherwise passed to the
pinned backend unchanged; this scaffold does not normalize, repair, or
substitute answers.

The default backend deliberately leaves timeouts to a future process-level
execution boundary, which must be specified and frozen before benchmark use.
