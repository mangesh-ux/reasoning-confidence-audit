# Experiment timeline

| Phase | Status | Purpose and boundary |
| --- | --- | --- |
| Q0–Q2 | Complete | Frozen setup, source inspection, and audit planning for the released CoDE-Stop path. |
| Q3 | Complete | Deterministic development trajectories and measurement-boundary observations. |
| Q4–Q5 | Complete | Offline analysis of frozen Q3 traces, including exploratory candidate-correctness ranking. |
| Q6 | Complete | Independent preregistered holdout measurement audit; no CoDE-Stop code change. |
| Q7 | Complete | Controlled fixed-prefix precision-fidelity study across Q4_K_M, Q8_0, selective BF16, and TQ1_0 stress probes. |
| M1 | Complete | Preregistered 16-example Q8_0 forced-answer measurement-semantics feasibility study; terminal decision: Measurement-paper path justified, with stated limits. |
| M2 | Stopped: runtime infeasible | Separately preregistered 100-example Q8_0 confirmatory measurement audit. It retained 18 valid pairs but did not meet the 80-pair minimum or start BF16. |
| P1 | Frozen and paused | Historical risk-controlled BAC protocol; paused at a direct prior-work gate and not an authorized next action. |

The completed phases are evidence about the released confidence measurement
and quantization fidelity under the stated conditions. M1 supports only a
narrow measurement-audit paper path. M2 is not a null-effect result, but it is
not confirmatory evidence because the frozen runtime did not complete the
design. Neither status alters Q0–Q7 artifacts or authorizes another signal or
new inference.

See [m1_forced_answer_measurement_semantics_decision.md](m1_forced_answer_measurement_semantics_decision.md),
[m2_runtime_feasibility_abort.md](m2_runtime_feasibility_abort.md), and the
retained [next_study_protocol.md](next_study_protocol.md) for the corresponding
records.
