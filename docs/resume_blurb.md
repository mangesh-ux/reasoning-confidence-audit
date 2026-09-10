# Resume blurb

- Reproduced and analyzed a recent method for stopping LLM reasoning early,
  building tools to inspect intermediate answers and token probabilities.
- Found that confidence could be strongly affected by text generated after the
  candidate answer; ending the probe at the answer boundary reduced
  trial-probe generation by 79% in a held-out accounting experiment.
- Tested quantization effects and found Q8 matched BF16 on 11 of 12
  fixed-prefix answers, while Q4 matched 5 of 12.
