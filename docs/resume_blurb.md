# Resume blurb

- Reproduced and audited confidence-based early stopping for a 4B reasoning model; found that probe confidence often included text generated after the answer was already complete.
- Built token-level probe instrumentation that ended at the candidate-answer boundary, showing a 79.37% counterfactual reduction in trial-probe generated tokens on an independent Q6 holdout.
- Ran a frozen Q4/Q8/BF16 precision check: Q8 matched BF16 on 11 of 12 candidate answers, versus 5 of 12 for Q4, guiding the next validation backend.
