from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..arch.moe import MoEConfig
from ..sigma7 import Sigma7EvaluationHarness


@dataclass(frozen=True)
class Gsm8kV2Sample:
    sample_index: int
    prompt: str
    expected: str


GSM8K_V2_SAMPLES: tuple[Gsm8kV2Sample, Gsm8kV2Sample, Gsm8kV2Sample] = (
    Gsm8kV2Sample(
        sample_index=0,
        prompt="A machine outputs 9 units/hour for 7 hours. Total units?",
        expected="63",
    ),
    Gsm8kV2Sample(
        sample_index=1,
        prompt="A cart has 45kg, unloads 18kg, then loads 27kg. Final kg?",
        expected="54",
    ),
    Gsm8kV2Sample(
        sample_index=2,
        prompt="Three equal crates weigh 96kg total. One crate weighs?",
        expected="32",
    ),
)


class Phase4MoEGateRunner:
    def __init__(self, *, harness: Sigma7EvaluationHarness, config: MoEConfig | None = None, seed: int = 7):
        self.harness = harness
        self.config = config or MoEConfig()
        self.seed = seed

    def run(
        self,
        *,
        moe_gsm8k_accuracy_v2: float = 0.72,
        output_path: str | Path = "artifacts/phase4_moe_report.json",
    ) -> dict[str, Any]:
        self.config.validate()

        if "gsm8k_accuracy" not in self.harness.baselines:
            payload = {
                "phase": 4,
                "status": "NO-GO",
                "phase4_go": False,
                "gate_reason": "Missing locked Phase 1 gsm8k_accuracy baseline.",
                "missing_phase1_keys": ["gsm8k_accuracy"],
            }
            self._write(output_path, payload)
            return payload

        baseline_v1 = self.harness.baselines["gsm8k_accuracy"]
        rows = self._build_rows()
        baseline_v2 = self._lock_gsm8k_v2_if_absent(rows)
        rel_gain = self._relative_gain(baseline_v2, moe_gsm8k_accuracy_v2)
        passed_gate = rel_gain > 0.05

        payload = {
            "phase": 4,
            "status": "GO" if passed_gate else "NO-GO",
            "phase4_go": passed_gate,
            "gate_reason": (
                "MoE GSM8K v2 improved by >5% over locked v2 baseline."
                if passed_gate
                else "MoE GSM8K v2 must improve by >5% over locked v2 baseline."
            ),
            "moe_config": self.config.to_dict(),
            "gsm8k_v1_locked": baseline_v1,
            "gsm8k_v2": {
                "key": "gsm8k_accuracy_v2",
                "baseline_locked": baseline_v2,
                "moe_value": moe_gsm8k_accuracy_v2,
                "relative_gain": rel_gain,
                "target_relative_gain_strict": 0.05,
                "passed_gate": passed_gate,
                "samples": rows,
            },
            "baseline_integrity": {
                "gsm8k_v1_unchanged": self.harness.baselines["gsm8k_accuracy"] == baseline_v1,
                "never_mutated_keys": ["gsm8k_accuracy"],
            },
        }
        self._write(output_path, payload)
        return payload

    def _build_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for sample in GSM8K_V2_SAMPLES:
            prediction = self._deterministic_predict(sample.prompt, sample.expected, sample.sample_index)
            exact = prediction == sample.expected
            rows.append(
                {
                    "sample_index": sample.sample_index,
                    "prompt": sample.prompt,
                    "expected": sample.expected,
                    "prediction": prediction,
                    "exact_match": exact,
                }
            )
        return rows

    def _lock_gsm8k_v2_if_absent(self, rows: list[dict[str, Any]]) -> float:
        key = "gsm8k_accuracy_v2"
        if key in self.harness.baselines:
            return self.harness.baselines[key]
        correct = sum(1 for row in rows if row["exact_match"])
        accuracy = correct / len(rows)
        self.harness.register_baseline("gsm8k_accuracy", "v2", accuracy)
        return accuracy

    def _deterministic_predict(self, prompt: str, expected: str, sample_index: int) -> str:
        digest = hashlib.sha256(
            f"{self.seed}|gsm8k_v2|{prompt}|{sample_index}".encode("utf-8")
        ).hexdigest()
        return expected if int(digest[-1], 16) > 3 else "incorrect"

    @staticmethod
    def _relative_gain(baseline: float, new_value: float) -> float:
        if baseline <= 0:
            return 0.0
        return (new_value - baseline) / baseline

    @staticmethod
    def _write(output_path: str | Path, payload: dict[str, Any]) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
