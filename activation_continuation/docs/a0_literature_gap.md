# A0 — Literature Gap and Prior-Work Gate

**Review date:** 2026-09-14
**Decision:** The exact controlled measurement question is not directly
preempted. The broad activation-guided continuation / stopping *method* space
is preempted by recent work. The authorized study may proceed only as a
predeclared validity study of whether an apparent activation signal survives
attempt-specific controls; it must not claim to introduce activation-based
early stopping.

## Question tested by this study

For a saved stochastic reasoning attempt at checkpoint `t`, this study defines
the realized gain

`gain = y_final - y_stop`,

where `y_stop` is correctness of a deterministic answer forced from the exact
saved prefix and `y_final` is correctness of that same saved trajectory's
uninterrupted continuation. Its primary label is `W -> C` (`gain = +1`). It is
not an unbiased expected reward or a causal counterfactual.

The narrow claim under review is therefore:

> Do prefix activations add held-out predictive information about realized
> `W -> C` continuation benefit beyond surface/question difficulty and frozen
> observable trajectory signals, including candidate-answer confidence, under
> within-problem or matched-checkpoint evaluation?

This is deliberately stricter than predicting final correctness, predicting
whether a forced exit is currently correct, or predicting an unconditional
expected value of additional tokens.

## Search and decision rule

Primary versions on arXiv, OpenReview, ACL Anthology, and linked official code
pages were checked on the review date. Searches covered the named papers in
the study brief and later work on activation probing, adaptive test-time
compute, recovery/overthinking, and reasoning early exit. `NR` below means the
property was not reported in the inspected primary source; it is not assumed
to be absent.

The hard stop rule was: stop before model inference if a primary source already
tests all of (a) an intermediate-activation predictor of attempt-specific
continuation benefit, (b) incremental value beyond difficulty and observable
confidence, and (c) held-out within-problem or matched-checkpoint evaluation.

**Hard-stop result: not triggered.** No reviewed primary source reports all
three elements together. This is not a license to recast existing
activation-guided stopping as new: Re-FORC and OS-Pruner already cover that
broader method idea.

## Closest work matrix

| Work and current primary version | Exact question / model and scale | Checkpoint and representation | Target and future/continuation outcome | Multiple attempts, difficulty control, within-problem analysis | Early stopping / code | Exact overlap and boundary |
| --- | --- | --- | --- | --- | --- | --- |
| [Re-FORC](https://arxiv.org/html/2511.02130v2), v2 (2026-07-24) | Whether a frozen Qwen3 reasoning model can estimate the value of additional thinking. Training uses DeepScaleR; the paper uses MC `N=8` continuations (`N=4` in one condition) and evaluates up to 32 samples/problem (4 for MATH500). | Regular prefix grid `0, 512, ..., 8192`; penultimate-layer activations pooled with self-attention. | Prefix-conditioned **expected** reward after resampled extra tokens, not a saved-attempt `y_final - y_stop` label. | Multiple continuations are used for MC value estimation. No question-only/difficulty baseline, additive observable-confidence baseline, or within-problem/matched-checkpoint test is reported. | Yes; expected marginal utility / Gittins-style stopping. Official implementation is linked by the paper. | Near-direct prior work for activation-informed continuation value and policy. It does **not** test the requested realized `W -> C` target or the required incremental and within-problem controls. |
| [OS-Pruner](https://arxiv.org/html/2607.11089v1), v1 (2026-07-13) | Whether a learned stopping policy can prune unnecessary reasoning. Model/dataset settings vary by experiment; report them from the pinned source if used as a baseline. | Paragraph boundaries; last hidden state, with the final two transformer layers fine-tuned. | Forced-final-answer grading and optimal-stopping value, rather than a reported `W -> C` predictor on an untouched original continuation. | NR for a difficulty-plus-observable incremental model and for held-out within-problem/matched-checkpoint discrimination. | Yes; learned optimal-stopping policy. Code status must be rechecked before any baseline execution. | Directly preempts a broad hidden-state stopping-method claim, but not the proposed validity test. |
| [It's the Problem, Not the Path](https://arxiv.org/html/2609.03436v1), v1 (2026-09-03) | Whether internal reasoning dynamics provide information beyond problem-level difficulty for eventual 16K-token success / scratch solvability. It studies 89 MATH problems across two models, with one base trajectory/cell and 4--8 continuations; it also reanalyses public data with 256 attempts/problem. | Final-layer state plus early hidden-geometry, entropy, and surprisal summaries at 16--8192-token anchors. | Eventual correctness and separately truncation-continuation rate versus matched-budget restarts, not forced-stop versus saved-continuation gain. | **Yes** for preregistered text-difficulty baselines, problem-grouped CV, and within-problem analysis: pooled performance can be high while the 256-attempt reanalysis is approximately neutral within problem. It does not include the proposed candidate-confidence control or `W -> C` target. | Matched-budget continuation/restart comparisons; no activation stopping policy. Code availability is reported by the source. | Closest validity warning. It motivates the design but does not answer the target question. |
| [Failed Reasoning Traces Tell You What Is Fixable](https://arxiv.org/html/2606.05145v1), v1 (2026-06-03) | Whether pools of failed traces reveal recoverability and route interventions; standard cells aggregate 10 failed rollouts/problem. | Log-probability/distributional geometry, not intermediate residual activations. | Recoverability / intervention choice, not deterministic forced-stop `W -> C`. | Per-problem rollout pools; no activation-plus-confidence incremental or checkpoint-level within-problem test. | Recovery routing; source/code availability as stated by paper. | Conceptually relevant recovery work, not a direct activation-continuation test. |
| [Reasoning Models Know When They're Right](https://arxiv.org/html/2504.05419v1), v1 (2025-04-07) | Whether hidden states predict correctness of intermediate and future intermediate answers; its MATH experiment uses R1-Distill-Llama-8B. | Paragraph/path-switch chunks; last-layer final-token state and a two-layer MLP. Chunk answers are labeled by Gemini versus gold. | Current/future answer correctness, not realized continuation gain. | Random 8:2 chunk-level split, not problem grouped; no question-only plus observable-confidence incremental or target-specific within-problem test. | Post-hoc first-threshold exit (about 24% of tokens on its MATH setting). | Prior correctness-probing / stopping work, not continuation-value evidence. |
| [LYNX](https://arxiv.org/html/2512.05325v1), v1 (2025-12-05) | Whether hidden states at natural reflection cues identify safe exits in one long rollout/problem. | `hmm`, `wait`, and `alternatively` cues; concatenated two middle-layer plus final-layer states. | Forced-exit correctness / safe stopping, not saved-trajectory `W -> C`. | One main rollout/problem; no requested difficulty-plus-observable or within-problem analysis reported. | Yes; split-conformal exit. It is a required closest executable hidden-state early-exit baseline if its official code is usable. | A policy baseline family; does not establish attempt-specific continuation gain. |
| [NEAT](https://arxiv.org/html/2602.02010v1), v1 (2026-02-02) | Whether a training-free neuron-activation termination pattern can suppress unnecessary reflection; its reference pattern is calibrated on 20 greedy MATH-train traces. | FFN-neuron activation pattern associated with `</think>` termination. | Termination state / stopping heuristic, not a controlled continuation-benefit label. | No requested controls or within-problem held-out test reported. | Yes; training-free reflection suppression. | Related activation stopping, not the proposed evidentiary question. |
| [ReProbe](https://arxiv.org/html/2511.06209v5), v5 (2026-04-23) | Whether a lightweight probe over hidden states, attention, or logits can assess reasoning-step credibility and select traces. | All-layer hidden states, attention, and logits; transformer step probe. | LLM-judged step correctness / trace quality, not original-continuation benefit. | Multi-trajectory search pruning, but no target-specific difficulty/confidence increment or within-problem test. | Selection/verification rather than same-attempt stopping. | Verification prior work only. |
| [STEP](https://arxiv.org/html/2601.09093v2), v2 (2026-04-28) | Whether hidden step states can prune parallel traces when memory is limited; training samples 64 solutions/problem. | Last-layer state at `\n\n` step boundaries. | Full-trace correctness propagated to every step. | Parallel trajectories, but no saved-attempt continuation-gain target or required controls. | Dynamic parallel pruning when the KV cache is saturated. | Not a sequential stop-versus-original-continuation study. |
| [CLUE](https://arxiv.org/html/2510.01591v1), v1 (2025-10-02) | Whether completed-trace hidden-state changes can distinguish correct from incorrect traces for reranking. | All-layer difference between the end of `</think>` and start of `<think>` on full completed solutions. | Completed-trace correctness. | No proposed controls/within-problem checkpoint test reported. | Reranking, not early exit. | Correctness verification, not continuation value. |
| [Are Language Models Aware of the Road Not Taken?](https://arxiv.org/html/2511.04527v1), v1 (2025-11-06) | Whether residual activations encode distributions over branched future outcomes and can be steered. The linear-probe illustration has 10 AQuA examples; other demonstrations use four deliberately uncertain examples across GSM8K, AQuA, and GPQA after 10 samples. | Residual `h_t` in a forked-path analysis. | Future-outcome distribution / steering behavior, not forced-stop `W -> C`. | Small, selected forked-path study; no required incremental controls or held-out within-problem `W -> C` prediction. | No comparable stopping policy. | Conceptually close only; different target and inferential design. |
| [Reasoning Theater: Disentangling Model Beliefs from CoT](https://arxiv.org/html/2603.05488v4), v4 (current at review) | Whether activation probes distinguish model beliefs from performative chain-of-thought behavior. Experiments include DeepSeek-R1-0528 and GPT-OSS-120B on MMLU-Redux and GPQA-D. | Context-pooled activation probes at intermediate positions, with forced answers. | Eventual multiple-choice answer / performativity, not a `W -> C` transition between a forced stop and the preserved original continuation. | No reported problem-grouped difficulty-plus-observable incremental probe or within-problem continuation-gain evaluation. | Includes probe-guided early exit; code availability must be verified before use. | Later direct-overlap threat and a potential closest executable policy baseline, but it does not answer the controlled target. |
| [Hidden Error Awareness in Chain-of-Thought Reasoning](https://arxiv.org/html/2605.09502v1), v1 (2026-05-10) | Whether hidden states identify final trace errors beyond verbal confidence, `P(True)`, and log probability. It uses 100 MATH500 training problems and 200 held-out problems. | Last-token state of a completed CoT and first-step state; logistic probe. | Final trace correctness. | Includes a partial within-problem check (five traces on 50 problems, correct versus wrong full-trace scores), but no forced-exit `W -> C`, question/difficulty control, or additive observable model. | Verification; selection/self-correction interventions did not establish an early-stopping policy. | Strong correctness-control reference, but not the requested test. |
| [CoDE-Stop](https://arxiv.org/html/2604.04930v2), v2 (2026-08-14) | Whether forced-answer token-confidence dynamics support early stopping. It reports Qwen3-4B/14B, R1-Distill-Llama-8B, and Nemotron-8B across AIME24/25, MATH500, GSM8K, and GPQA-D. | Forced answers at `Wait`/paragraph checkpoints; selected-token average probability and degeneration dynamics. | Observable confidence, not hidden activations. | Some datasets use multiple rollouts/problem (15/2/1/5 by reported benchmark), but there is no within-problem attempt comparison, difficulty control, or realized gain target. | Yes; released method/code. | Required observable-confidence baseline infrastructure, not prior activation evidence. |
| [ThinkBrake](https://arxiv.org/html/2510.00546v5), v5 (2026-04-20) | Whether the log-probability margin between continuation and `</think>` supports early exit. | Sentence boundaries; output-logit margin. | Heuristic stopping signal. | No activation target or requested controls. | Yes; code status per source. | Observable/logit stopping baseline family. |
| [TRACE](https://arxiv.org/html/2604.17304v1), v1 (2026-04-19) | Whether temporal aggregation of answer consistency and confidence trajectories supports stopping. | Answer/confidence trajectory. | Observable stopping signal. | No hidden activation target or requested controls. | Yes; code status per source. | Observable trajectory baseline family. |
| [Tracing the Traces](https://arxiv.org/html/2510.10494v1), v1 (2025-10-13; a distinct possible expansion of “TRACE”) | Whether all-layer hidden trajectories can select which of five reasoning paths should continue. It covers GPQA-198, AIME25-30, and TSP-180 with R1-D 14B, Phi-4R+, and Qwen3-14B. | All-layer hidden trajectories in 500-token segments; partial 500-token checkpoints; Net/Cumulative/Aligned Change features. | Final correctness / path selection, not saved-trajectory continuation gain. | Five independent traces/problem, but no difficulty-plus-observable increment or within-problem probe evaluation. | Multi-path early selection, not terminating one saved trajectory. | Strong activation prior art; not the proposed target. |
| [DTSR](https://arxiv.org/html/2604.06787v1), v1 (2026-04-08) | Whether reflection cues followed by a thought-sufficiency check can regulate reasoning. | Self-evaluation / sufficiency check. | Thought sufficiency, not realized continuation gain. | No requested activation controls. | Yes; source implementation status must be verified if selected. | Related early-exit framework, not the proposed claim. |

## Implications for protocol and claims

1. The study's novelty cannot be “hidden activations predict continuation
   value” or “activation-guided early stopping.” Those claims are occupied by
   Re-FORC and OS-Pruner.
2. The only defensible contribution is a controlled measurement question:
   whether a putative continuation signal remains after question difficulty,
   observable candidate confidence, checkpoint progress, and within-problem
   structure are respected. A null or difficulty-confounded result is an
   equally successful execution of that question.
3. No policy claim is authorized by this gate. A policy phase remains
   conditional on a predeclared practically meaningful held-out incremental
   signal, and any comparison with Re-FORC or OS-Pruner must use faithfully
   executable released code. An unavailable implementation will be reported as
   unavailable, not approximated.
4. This is a fully separate study from P1. No Q0--Q7, M1, M2, L1, P1,
   CoDE-Stop source, frozen outputs, or historical samples may be altered or
   used for selection/tuning. Historical work may appear only as motivation or
   baseline infrastructure.

## A0 terminal classification

**GAP NARROW BUT OPEN — CONTROLLED VALIDITY STUDY ONLY.** Proceed to a
non-benchmark runtime qualification only if the resulting protocol preserves
the constraints above. If a later primary-source update supplies the complete
hard-stop combination, halt before benchmark inference and record the new
source rather than manufacturing a distinction.
