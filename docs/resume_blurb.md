# Resume blurb

- Reproduced and analyzed a recent method for stopping LLM reasoning early,
  building tools to inspect intermediate answers and token probabilities.
- Found that confidence could be strongly affected by text generated after the
  candidate answer; boundary termination yielded a 79.37% counterfactual
  reduction in trial-probe generated tokens on the Q6 holdout.
- Tested quantization effects and found Q8 matched BF16 on 11 of 12
  fixed-prefix answers, while Q4 matched 5 of 12.
- Completed a preregistered Q8_0 forced-answer measurement-semantics
  feasibility study; its paired result supports only a narrow audit-paper path,
  not a new stopping method or safe threshold.
