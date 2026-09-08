from __future__ import annotations

from cryptex_x.quant.ternary import (
    absmean_scale,
    generate_synthetic_tensor,
    ternarize_tensor,
)


def test_generate_synthetic_tensor_128x128():
    weights = generate_synthetic_tensor(rows=128, cols=128, seed=7)
    assert len(weights) == 128
    assert all(len(row) == 128 for row in weights)


def test_ternary_absmean_and_value_set():
    weights = generate_synthetic_tensor(rows=128, cols=128, seed=7)
    scale = absmean_scale(weights)
    quantized = ternarize_tensor(weights)

    assert quantized["shape"] == [128, 128]
    assert quantized["scale"] == scale
    values = {v for row in quantized["values"] for v in row}
    assert values.issubset({-1, 0, 1})
