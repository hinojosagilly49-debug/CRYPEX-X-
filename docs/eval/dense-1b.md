# Dense 1B architecture card (Phase 1 baseline)

This card defines the fixed dense Transformer baseline used for Phase 1 locking.

## Model identity

- `model_name`: `dense-transformer-baseline`
- `model_scale`: `1B`
- `tokenizer`: `cl100k-like`
- `context_length`: `64000`
- precision: `fp16`

## Architecture fields

- `layer_count`: `TBD` (placeholder; not finalized in this repository)
- `d_model`: `TBD`
- `n_heads`: `TBD`
- `vocab_size`: `TBD`
- feed-forward type: dense (no sparse experts)

## Explicit exclusions

- No MoE routing
- No SSM/Mamba blocks
- No hybrid attention cadence

## Compute reference

Phase 1 dense baseline is the `1.0x` compute reference for all later ablations.

## Weights and training scope

This repository does not claim trained 1B weights.  
Phase 1 here is an evaluation-harness baseline lock using deterministic simulators and JSON artifacts.
