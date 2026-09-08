# Phase 6 quantization — 1.58-bit ternary absmean

This phase uses ternary quantization with absmean scaling on a synthetic tensor.

## Spec

- Tensor shape: `128 x 128` synthetic weights
- Scale: `scale = mean(abs(w))`
- Quantized value set: `{-1, 0, 1}`

## Mapping rule

- `w > scale  -> 1`
- `w < -scale -> -1`
- otherwise `0`

## Notes

- This repository uses deterministic synthetic tensors for evaluation stubs.
- No trained model weights are introduced by this phase.
