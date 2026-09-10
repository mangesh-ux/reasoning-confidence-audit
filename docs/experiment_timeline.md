# Experiment timeline

| Phase | Status | Purpose and boundary |
| --- | --- | --- |
| Q0–Q2 | Complete | Frozen setup, source inspection, and audit planning for the released CoDE-Stop path. |
| Q3 | Complete | Deterministic development trajectories and measurement-boundary observations. |
| Q4–Q5 | Complete | Offline analysis of frozen Q3 traces, including exploratory candidate-correctness ranking. |
| Q6 | Complete | Independent preregistered holdout measurement audit; no CoDE-Stop code change. |
| Q7 | Complete | Controlled fixed-prefix precision-fidelity study across Q4_K_M, Q8_0, selective BF16, and TQ1_0 stress probes. |
| Next study | Protocol corrected and frozen; not run | Boundary-Aligned Confidence under Risk-Controlled Early Stopping on 200 deterministically selected MATH500 examples: 100 calibration and 100 untouched test. |

The completed phases are evidence about the released confidence measurement
and quantization fidelity under the stated conditions. The next study is the
only proposed extension. It does not alter Q0–Q7 artifacts, add another signal,
or start until its manifest and calibration gates are satisfied.

See [next_study_protocol.md](next_study_protocol.md) for its full preregistered
plan and [protocol_feasibility.md](protocol_feasibility.md) for the
pre-inference calibration-size correction.
