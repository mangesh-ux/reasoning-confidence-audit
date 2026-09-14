# M2 Runtime-Feasibility Abort Record

## Terminal status

**EFFECT NOT CONFIRMED — runtime infeasible.**

This is not an estimate of a null semantic effect. The result follows from
the preregistered M2 confirmation rule: the run produced only 18 primary valid
paired checkpoints, below the fixed minimum of 80, and could not proceed to
the required BF16 anchor.

## What occurred

The immutable M2 freeze was bound to
e53f8570e4b897a92838b55d8e9486d1cdcc32ec91ff320999cb6fd5673a99ca.
Both Q8_0 and BF16 load-only preflights passed with zero completion requests.

In the Q8_0 primary run, six base trajectories completed and yielded 18
completed, primary-valid shared probes. One subsequent base completion with a
65-token input stalled midway through decoding at 1,598 generated tokens,
below both the configured context and generation limits. The single-slot
server did not recover, so the next base request timed out downstream. The
following request had a durable intent but no outcome when the run was stopped;
it is retained as an interrupted-unknown outcome. The remaining 91 selected
examples were never started.

No failed request was retried, replaced, shortened, or repaired. No M1
artifact was modified. No BF16 anchor request, second benchmark, M3 study, or
post-hoc analysis was run.

## Required interpretation

The frozen Q8_0 runtime did not complete the authorized M2 design under its
fixed context and generation settings. Accordingly, M2 does not establish a
confirmatory effect, a weak/mixed semantic result, an absence of an effect, a
new confidence metric, a stopping method, or any cost-saving claim.

Any future attempt to address this runtime failure requires a separately
authorized protocol; it cannot silently change the frozen M2 context,
generation budget, runtime, sample, or retry policy.
