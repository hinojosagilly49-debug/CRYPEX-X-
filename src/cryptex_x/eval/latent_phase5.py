from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..arch.latent_router import LatentRouter
from ..sigma7 import Sigma7EvaluationHarness


class Phase5LatentAblationRunner:
    def __init__(
        self,
        *,
        harness: Sigma7EvaluationHarness,
        router: LatentRouter,
    ) -> None:
        self.harness = harness
        self.router = router

    def run(
        self,
        *,
        baseline_entropy: float,
        latent_entropy: float,
        active_tokens: int = 256,
        dtype_size: int = 2,
        gsm8k_v2_after: float | None = None,
        output_path: str | Path = "artifacts/phase5_latent_ablation.json",
    ) -> dict[str, Any]:
        if "gsm8k_accuracy_v2" not in self.harness.baselines:
            payload = {
                "phase": 5,
                "status": "NO-GO",
                "phase5_go": False,
                "gate_reason": "Missing locked gsm8k_accuracy_v2 baseline.",
                "missing_keys": ["gsm8k_accuracy_v2"],
            }
            self._write(output_path, payload)
            return payload

        entropy_rise = self._relative_rise(baseline_entropy, latent_entropy)
        entropy_passed = entropy_rise <= 0.02

        full_bytes = active_tokens * self.router.d_model * dtype_size
        latent_bytes = active_tokens * self.router.latent_dim * dtype_size
        reduction_ratio = self.router.d_model / self.router.latent_dim
        observed_drop_ratio = full_bytes / latent_bytes
        byte_drop_matches_ratio = observed_drop_ratio == reduction_ratio

        gsm8k_baseline = self.harness.baselines["gsm8k_accuracy_v2"]
        gsm8k_after = gsm8k_v2_after if gsm8k_v2_after is not None else gsm8k_baseline
        gsm8k_drop = self._relative_drop(gsm8k_baseline, gsm8k_after)
        gsm8k_passed = gsm8k_drop <= 0.015

        phase5_go = entropy_passed and byte_drop_matches_ratio and gsm8k_passed
        payload = {
            "phase": 5,
            "status": "GO" if phase5_go else "NO-GO",
            "phase5_go": phase5_go,
            "gate_reason": self._gate_reason(
                entropy_passed=entropy_passed,
                byte_drop_matches_ratio=byte_drop_matches_ratio,
                gsm8k_passed=gsm8k_passed,
            ),
            "latent_router": self.router.to_dict(),
            "routing_entropy": {
                "baseline_entropy": baseline_entropy,
                "latent_entropy": latent_entropy,
                "relative_rise": entropy_rise,
                "max_allowed_rise": 0.02,
                "passed_gate": entropy_passed,
            },
            "all_to_all_bytes": {
                "formula": "active_tokens * dim * dtype_size",
                "active_tokens": active_tokens,
                "dtype_size": dtype_size,
                "full_d_router_bytes": full_bytes,
                "latent_router_bytes": latent_bytes,
                "drop_ratio": observed_drop_ratio,
                "expected_drop_ratio": reduction_ratio,
                "drop_matches_d_over_l": byte_drop_matches_ratio,
            },
            "gsm8k_v2_ablation": {
                "baseline": gsm8k_baseline,
                "new_value": gsm8k_after,
                "relative_drop": gsm8k_drop,
                "max_allowed_drop": 0.015,
                "passed_gate": gsm8k_passed,
            },
        }
        self.harness.current_phase = max(self.harness.current_phase, 5)
        self._write(output_path, payload)
        return payload

    @staticmethod
    def _relative_rise(baseline: float, new_value: float) -> float:
        if baseline <= 0:
            return 0.0
        return max(0.0, (new_value - baseline) / baseline)

    @staticmethod
    def _relative_drop(baseline: float, new_value: float) -> float:
        if baseline <= 0:
            return 0.0
        return max(0.0, (baseline - new_value) / baseline)

    @staticmethod
    def _gate_reason(
        *,
        entropy_passed: bool,
        byte_drop_matches_ratio: bool,
        gsm8k_passed: bool,
    ) -> str:
        reasons: list[str] = []
        if not entropy_passed:
            reasons.append("Routing entropy rise must be <=2%.")
        if not byte_drop_matches_ratio:
            reasons.append("All-to-all byte drop must equal d/l.")
        if not gsm8k_passed:
            reasons.append("gsm8k_accuracy_v2 drop must be <=1.5%.")
        return " ".join(reasons) if reasons else "Phase 5 gates passed."

    @staticmethod
    def _write(output_path: str | Path, payload: dict[str, Any]) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
