from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LatentRouter:
    d_model: int
    latent_dim: int = 16

    def __post_init__(self) -> None:
        if self.d_model <= 0:
            raise ValueError("d_model must be > 0")
        if self.latent_dim <= 0:
            raise ValueError("latent_dim must be > 0")
        if self.latent_dim >= self.d_model:
            raise ValueError("latent_dim must be smaller than d_model (ℓ ≪ d)")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reduction_ratio"] = self.d_model / self.latent_dim
        payload["reduction_formula"] = "d_model / latent_dim"
        return payload


def serialize_phase5_latent_router(
    router: LatentRouter,
    *,
    output_path: str | Path = "artifacts/phase5_latent_router.json",
) -> dict[str, Any]:
    payload = {"phase": 5, "latent_router": router.to_dict()}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
