# Hybrid Mamba backbone (Phase 2)

Phase 2 uses a hybrid backbone that interleaves SSM blocks (`mamba2`) with periodic global attention.

## Attention cadence

- Supported global-attention cadence range: **1/4 to 1/12**
- Default config in this repository: **1/8** (`attn_every=8`)

## GO / NO-GO rule

Phase 2 is **GO** only if all of the following pass:

1. Required Phase 1 locks exist (`mmlu_accuracy`, `gsm8k_accuracy`, `ruler_miss_rate`)
2. Decode gain is strictly **>30%** vs decode baseline
3. MMLU drop is **<1%** vs locked baseline
4. ARC drop is **<1%** vs locked baseline (or `arc_pending` when ARC baseline is not yet locked)
5. `kv_cache_vs_dense <= 0.30` (lower is better), with:
   - `kv_cache_vs_dense = hybrid_kv_cache_bytes / dense_kv_cache_bytes`
