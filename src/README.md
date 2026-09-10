# Reusable audit tooling

`reasoning_confidence` is a small, standard-library-only Python package that
exposes the reusable instrumentation behind this audit. It is designed for
synthetic testing or a separately configured local llama.cpp completion server;
it does not contain a model runner or private experiment artifacts.

## Public modules

- `boundary.py` finds the matching outer `\boxed{...}` close, tracks nested
  braces, reports malformed or incomplete candidates, and maps that boundary
  onto generated token pieces.
- `confidence.py` reconstructs the released full-span quantity and
  Boundary-Aligned Confidence (BAC). BAC includes only token positions strictly
  between the opening and closing outer-brace tokens, matching the frozen Q7
  convention.
- `checkpoints.py` exposes the released-style, upstream-specific interpretation
  of individual `Wait` token IDs and EOS membership. It is not a universal
  checkpoint detector.
- `probe.py` provides an explicit client for greedy, one-token `/completion`
  calls to an already running local llama.cpp server. It never starts a server
  and has no hard-coded path, port, model, or artifact location.
- `metrics.py` contains compact helpers for normalized candidate agreement,
  paired confidence comparisons, and probe-token accounting.

There are two deliberate parser modes. `find_first_boxed_boundary` uses the
offline audit convention that ignores escaped braces. The forced-probe parser
uses the frozen Q7 literal-brace behavior and requires the generated candidate
to begin with the opening outer brace. Both modes report malformed or no-close
outcomes instead of trying to repair them.

The released full-span reconstruction preserves the audited denominator:
it sums generated positions `1` through `n-2` and divides by `n-1`. BAC is the
ordinary geometric mean of the included candidate-token probabilities. Neither
function clips, calibrates, or replaces the measurement with a new metric;
non-finite values are rejected.

## Quick check

From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python examples\synthetic_probe_demo.py
```

The tests and example are synthetic: they need no GPU, model weights, dataset,
network connection, or live server.

## Aggregate result packager

`rebuild_public_results.py` is a separate standard-library result-packaging
instrument. It reads compact public inputs or Q3–Q7 aggregate JSON from a
separate frozen artifact tree, records source hashes, and writes the public
summary schema.

It does not load weights, start a server, generate tokens, modify CoDE-Stop,
select a threshold, or alter frozen artifacts. The public result-rebuild path
is described in the root [README](../README.md).

This package is an independent implementation of documented audit semantics;
no upstream CoDE-Stop, llama.cpp, or Conformal Thinking code is copied or
vendored here.
