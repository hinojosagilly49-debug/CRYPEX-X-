from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HybridConfig:
    attn_every: int = 8
    ssm: str = "mamba2"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["global_attention_ratio"] = f"1/{self.attn_every}"
        payload["global_attention_fraction"] = 1 / self.attn_every
        return payload


def serialize_phase2_hybrid_config(
    config: HybridConfig | None = None,
    *,
    output_path: str | Path = "artifacts/phase2_hybrid_config.json",
) -> dict[str, Any]:
    cfg = config or HybridConfig()
    payload = {"phase": 2, "hybrid_config": cfg.to_dict()}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
