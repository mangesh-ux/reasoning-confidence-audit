# M2 Literature Gate: Confirmatory Forced-Answer Measurement Audit

> **Release status (2026-09-14):** This is M2's frozen pre-inference literature
> gate. It is retained to document the prospective overlap check; M2 later
> stopped for runtime infeasibility rather than reaching a confirmatory
> analysis. See the [abort record](m2_runtime_feasibility_abort.md). This
> status note is not part of the frozen gate body.

## Scope

M2 is constrained to a code-to-boundary measurement/reproducibility audit of
the pinned CoDE-Stop release. It cannot claim a new answer-only confidence
metric, a generic forced-answer stopping method, a threshold-safety result, or
end-to-end reasoning savings. This gate is a prospective literature review,
not a reinterpretation of M1 or frozen Q0-Q7 evidence.

## Prior work that closes broad novelty claims

- The CoDE-Stop paper and pinned source release establish the named
  implementation being audited. M2 treats the source behavior as a released
  semantics target, not as an algorithm to modify:
  https://arxiv.org/html/2604.04930 and
  https://github.com/sudoparsa/CoDE-Stop/tree/b5081e7c2abe23bb1d19649421cc13522fee7c50
- REFRAIN evaluates answer-only likelihood inside a boxed region. It closes
  any claim that a boxed-answer geometric-mean likelihood is itself new:
  https://aclanthology.org/2026.acl-long.1256/
- Conformal Thinking already combines forced boxed answers, answer likelihood,
  and calibration/risk-control framing. It closes generic integration novelty:
  https://arxiv.org/html/2602.03814 and
  https://github.com/xidulu/reasoning_risk_control
- Kim and Kang study calibration sensitivity to answer-context and readout
  protocol choices:
  https://arxiv.org/html/2605.27752
- Datta et al. study forced answer completion and redundant reasoning:
  https://arxiv.org/html/2604.22266

## Narrow unresolved question

The literature review asks a much narrower question: does a public source
already provide a paired empirical audit that reconstructs the pinned
CoDE-Stop release's token-ID terminal behavior, 21-token cap, endpoint score
formula, and exact matching outer-box boundary on the same greedy trace?

The pre-inference search reviewed the primary sources above plus targeted
queries for CoDE-Stop candidate boundary, released terminal token,
forced-answer measurement semantics, and calibration protocol sensitivity. No
primary public source was located that supplies that exact audit. This is a
bounded search finding, not a claim that no related work exists.

## Bounded recheck: 2026-09-14

The pre-inference recheck reviewed the current CoDE-Stop v2 paper and pinned
release, REFRAIN, Conformal Thinking, Kim and Kang's protocol-sensitivity
study, and Datta et al.'s forced-answer study. It also searched for the
combination of CoDE-Stop, candidate boundary, released terminal behavior, and
shared greedy forced-answer traces. No primary public source located in that
bounded review supplies the exact paired audit defined above.

The recheck also located recent work on calibration under context shifts. That
work reinforces the need to preserve fixed elicitation semantics, but it does
not perform the released-CoDE-to-outer-boundary reconstruction. It therefore
does not create an exact-overlap stop condition and does not enlarge M2's
claims.

If an exact public overlap is located before any M2 model completion or before
the terminal decision, preserve the protocol and stop empirical expansion to
report the overlap. A related answer-only score, forced-answer method, or
calibration paper is not by itself an exact overlap; it instead narrows M2's
allowed claims as stated above.

## Reporting boundary

If run, M2 may report only the measured difference between two fixed
interpretations of the named release on its stated model, runtime, dataset
revision, cohort, and precision anchor. It may not turn a favorable result
into a claim that boundary scoring is novel, calibrated, safe, generically
better, or a realized end-to-end efficiency improvement.
