from __future__ import annotations

from typing import Any


def mask_6_8(weights: list[list[int]]) -> dict[str, Any]:
    masked: list[list[int]] = []
    kept = 0
    total = 0
    for row in weights:
        out_row: list[int] = []
        for i, value in enumerate(row):
            keep = (i % 8) < 6
            out_row.append(value if keep else 0)
            kept += 1 if keep else 0
            total += 1
        masked.append(out_row)
    density = kept / total if total else 0.0
    return {"values": masked, "density": density}
