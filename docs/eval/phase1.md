# Phase 1 — Dense baseline lock semantics

Phase 1 GO is a lock-completeness gate, not a benchmark-target gate.

## Rule

- `phase1_go` is `True` **iff** all three baseline keys are successfully locked:
  - `mmlu_accuracy`
  - `gsm8k_accuracy`
  - `ruler_miss_rate`
- If any lock attempt fails (for example, a key is already locked), Phase 1 is `NO-GO`.

## Targets vs gate outcome

Each benchmark row records `passed_target` independently:

- `passed_target=True` means that single benchmark hit its target threshold.
- `passed_target=False` means it missed the target threshold.

These per-benchmark target outcomes do **not** decide Phase 1 GO.  
Phase 1 GO only checks whether all required baselines were produced and locked without overwrite.
