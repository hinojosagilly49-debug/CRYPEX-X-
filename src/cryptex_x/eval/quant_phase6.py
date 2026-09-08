from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..quant.ternary import generate_synthetic_tensor, ternarize_tensor
from ..sigma7 import Sigma7EvaluationHarness


class Phase6QuantGateRunner:
    def __init__(self, *, harness: Sigma7EvaluationHarness):
        self.harness = harness

    def run(
        self,
        *,
        mmlu_new: float,
        gsm8k_new: float,
        arc_new: float,
        output_path: str | Path = "artifacts/phase6_quant_report.json",
    ) -> dict[str, Any]:
        weights = generate_synthetic_tensor(rows=128, cols=128, seed=7)
        quantized = ternarize_tensor(weights)

        bits_per_weight = 1.58
        dense_bits_per_weight = 16.0
        size_ratio = bits_per_weight / dense_bits_per_weight
        size_passed = size_ratio <= 0.16

        baselines = {
            "mmlu": self.harness.baselines.get("mmlu_accuracy", 0.3333333333333333),
            "gsm8k": self.harness.baselines.get("gsm8k_accuracy_v2", 2 / 3),
            "arc": self.harness.baselines.get("arc_challenge_accuracy", 2 / 3),
        }
        new_values = {
            "mmlu": mmlu_new,
            "gsm8k": gsm8k_new,
            "arc": arc_new,
        }
        quide_by_metric = {
            metric: 0.02 - max(0.0, baselines[metric] - new_values[metric])
            for metric in ("mmlu", "gsm8k", "arc")
        }
        quide_index = min(quide_by_metric.values())
        quide_passed = quide_index > 0

        mmlu_drop = self._relative_drop(baselines["mmlu"], mmlu_new)
        mmlu_drop_passed = mmlu_drop < 0.02

        phase6_go = size_passed and quide_passed and mmlu_drop_passed
        payload = {
            "phase": 6,
            "status": "GO" if phase6_go else "NO-GO",
            "phase6_go": phase6_go,
            "gate_reason": self._gate_reason(
                size_passed=size_passed,
                quide_passed=quide_passed,
                mmlu_drop_passed=mmlu_drop_passed,
            ),
            "size": {
                "bits_per_weight": bits_per_weight,
                "dense_bits_per_weight": dense_bits_per_weight,
                "size_ratio": size_ratio,
                "target_max_ratio": 0.16,
                "passed_gate": size_passed,
            },
            "quide": {
                "formula": "0.02 - max(0, baseline_acc - new_acc)",
                "per_metric": quide_by_metric,
                "index": quide_index,
                "passed_gate": quide_passed,
            },
            "mmlu_drop": {
                "baseline": baselines["mmlu"],
                "new_value": mmlu_new,
                "relative_drop": mmlu_drop,
                "reject_if_drop_gte": 0.02,
                "passed_gate": mmlu_drop_passed,
            },
            "ternary_tensor": {
                "shape": quantized["shape"],
                "scale": quantized["scale"],
                "value_set": sorted({v for row in quantized["values"] for v in row}),
            },
        }
        self.harness.current_phase = max(self.harness.current_phase, 6)
        self._write(output_path, payload)
        return payload

    @staticmethod
    def _relative_drop(baseline: float, new_value: float) -> float:
        if baseline <= 0:
            return 0.0
        return max(0.0, (baseline - new_value) / baseline)

    @staticmethod
    def _gate_reason(*, size_passed: bool, quide_passed: bool, mmlu_drop_passed: bool) -> str:
        reasons: list[str] = []
        if not size_passed:
            reasons.append("size_ratio must be <= 0.16.")
        if not quide_passed:
            reasons.append("QuIDE index must be > 0.")
        if not mmlu_drop_passed:
            reasons.append("MMLU drop must be <2%.")
        return " ".join(reasons) if reasons else "Phase 6 gates passed."

    @staticmethod
    def _write(output_path: str | Path, payload: dict[str, Any]) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
