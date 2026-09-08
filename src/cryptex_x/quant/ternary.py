from __future__ import annotations

import hashlib
from typing import Any


def generate_synthetic_tensor(
    *,
    rows: int = 128,
    cols: int = 128,
    seed: int = 7,
) -> list[list[float]]:
    tensor: list[list[float]] = []
    for r in range(rows):
        row: list[float] = []
        for c in range(cols):
            h = hashlib.sha256(f"{seed}|{r}|{c}".encode("utf-8")).hexdigest()
            value = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
            row.append(value)
        tensor.append(row)
    return tensor


def absmean_scale(weights: list[list[float]]) -> float:
    flat = [abs(v) for row in weights for v in row]
    if not flat:
        return 0.0
    return sum(flat) / len(flat)


def ternarize_tensor(weights: list[list[float]]) -> dict[str, Any]:
    scale = absmean_scale(weights)
    quantized: list[list[int]] = []
    for row in weights:
        qrow: list[int] = []
        for value in row:
            if value > scale:
                qrow.append(1)
            elif value < -scale:
                qrow.append(-1)
            else:
                qrow.append(0)
        quantized.append(qrow)
    return {
        "shape": [len(weights), len(weights[0]) if weights else 0],
        "scale": scale,
        "values": quantized,
    }
