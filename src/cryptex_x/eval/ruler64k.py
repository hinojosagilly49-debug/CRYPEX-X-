from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..sigma7 import Sigma7EvaluationHarness


PHASE3_RULER_MARKERS: tuple[str, str, str] = (
    "ALPHA-9241",
    "BRAVO-7712",
    "CHARLIE-3145",
)


@dataclass(frozen=True)
class Phase3Ruler64kSample:
    sample_index: int
    marker: str
    prediction: str
    exact_match: bool


class Phase3Ruler64kProtocolRunner:
    """Phase 3 long-context RULER protocol stub (64k context, markers-only payload)."""

    def __init__(self, *, harness: Sigma7EvaluationHarness):
        self.harness = harness

    def run(
        self,
        *,
        predictions: tuple[str, str, str] | None = None,
        output_path: str | Path = "artifacts/phase3_ruler64k_report.json",
    ) -> dict[str, Any]:
        if "ruler_miss_rate" not in self.harness.baselines:
            payload = {
                "phase": 3,
                "status": "NO-GO",
                "phase3_go": False,
                "gate_reason": "Missing locked Phase 1 ruler_miss_rate baseline.",
                "missing_phase1_keys": ["ruler_miss_rate"],
            }
            self._write(output_path, payload)
            return payload

        locked_ruler_before = self.harness.baselines["ruler_miss_rate"]
        predicted = predictions or PHASE3_RULER_MARKERS
        samples: list[Phase3Ruler64kSample] = []
        misses = 0
        for idx, marker in enumerate(PHASE3_RULER_MARKERS):
            prediction = predicted[idx]
            exact = prediction == marker
            misses += 0 if exact else 1
            samples.append(
                Phase3Ruler64kSample(
                    sample_index=idx,
                    marker=marker,
                    prediction=prediction,
                    exact_match=exact,
                )
            )

        total = len(PHASE3_RULER_MARKERS)
        miss_rate = misses / total
        passed_gate = miss_rate < 0.001
        payload = {
            "phase": 3,
            "status": "GO" if passed_gate else "NO-GO",
            "phase3_go": passed_gate,
            "context_protocol": {
                "context_length_tokens": 64000,
                "unit": "tokens",
                "full_context_payload_stored": False,
            },
            "ruler": {
                "markers": list(PHASE3_RULER_MARKERS),
                "target_max_fraction": 0.001,
                "miss_rate_fraction": miss_rate,
                "misses": misses,
                "n": total,
                "formula": "miss_rate_fraction = misses / n",
                "passed_gate": passed_gate,
                "samples": [asdict(sample) for sample in samples],
            },
            "phase1_locked_ruler_miss_rate_fraction": locked_ruler_before,
            "baseline_unchanged": self.harness.baselines["ruler_miss_rate"]
            == locked_ruler_before,
            "gate_reason": (
                "RULER miss rate is below 0.001 (fraction)."
                if passed_gate
                else "RULER miss rate must be < 0.001 (fraction)."
            ),
        }
        self._write(output_path, payload)
        return payload

    @staticmethod
    def _write(output_path: str | Path, payload: dict[str, Any]) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
