from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MoEConfig:
    n_experts: int = 8
    top_k: int = 1
    active_flops_ratio: float = 1.0
    active_flops_tolerance: float = 1e-6

    def validate(self) -> None:
        if self.n_experts < 1:
            raise ValueError("n_experts must be >= 1")
        if self.top_k < 1 or self.top_k > self.n_experts:
            raise ValueError("top_k must be in [1, n_experts]")
        if abs(self.active_flops_ratio - 1.0) > self.active_flops_tolerance:
            raise ValueError("active_flops_ratio must remain 1.0±1e-6")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["active_flops_invariant"] = "1.0±1e-6"
        return payload
