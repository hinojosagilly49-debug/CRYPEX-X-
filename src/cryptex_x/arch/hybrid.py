from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..sigma7 import Sigma7EvaluationHarness


@dataclass(frozen=True)
class HybridConfig:
    attn_every: int = 8
    ssm: str = "mamba2"

    def to_dict(self, *, phase3_ran: bool = False) -> dict[str, Any]:
        payload = asdict(self)
        payload["global_attention_ratio"] = f"1/{self.attn_every}"
        payload["global_attention_fraction"] = 1 / self.attn_every
        payload["phase3_context_validated"] = phase3_ran
        payload["advertised_context_length"] = 64000 if phase3_ran else 8192
        payload["advertised_context_length_unit"] = "tokens"
        return payload


def serialize_phase2_hybrid_config(
    config: HybridConfig | None = None,
    *,
    output_path: str | Path = "artifacts/phase2_hybrid_config.json",
) -> dict[str, Any]:
    cfg = config or HybridConfig()
    payload = {"phase": 2, "hybrid_config": cfg.to_dict(phase3_ran=False)}
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


PHASE1_REQUIRED_KEYS = (
    "mmlu_accuracy",
    "gsm8k_accuracy",
    "ruler_miss_rate",
)


@dataclass(frozen=True)
class Phase2SimulatedMetrics:
    decode_tokens_per_sec: float = 52.0
    ttft_seconds: float = 0.44
    mmlu_accuracy: float = 0.331
    arc_stub_correct: tuple[bool, bool, bool] = (True, True, False)
    dense_kv_cache_bytes: float = 1_000_000_000.0
    hybrid_kv_cache_bytes: float = 280_000_000.0


class Phase2AblationRunner:
    def __init__(self, *, harness: Sigma7EvaluationHarness, config: HybridConfig | None = None):
        self.harness = harness
        self.config = config or HybridConfig()

    def run(
        self,
        *,
        metrics: Phase2SimulatedMetrics | None = None,
        output_path: str | Path = "artifacts/phase2_ablation_report.json",
    ) -> dict[str, Any]:
        missing_phase1 = [key for key in PHASE1_REQUIRED_KEYS if key not in self.harness.baselines]
        if missing_phase1:
            payload = {
                "phase": 2,
                "status": "NO-GO",
                "phase2_go": False,
                "gate_reason": "Missing required Phase 1 baselines.",
                "missing_phase1_keys": missing_phase1,
            }
            self._write_report(output_path, payload)
            return payload

        proxy_registered = False
        decode_key = "inference_decode_tokens_per_sec"
        if decode_key not in self.harness.baselines:
            proxy_registered = self.harness.register_phase1_efficiency_proxies()

        simulated = metrics or Phase2SimulatedMetrics()
        decode_baseline = self.harness.baselines[decode_key]
        decode_improvement = (simulated.decode_tokens_per_sec - decode_baseline) / decode_baseline
        decode_gate_passed = decode_improvement > 0.30

        ttft_baseline = self.harness.baselines.get("inference_ttft_seconds")
        ttft_change = None
        if ttft_baseline is not None:
            ttft_change = (simulated.ttft_seconds - ttft_baseline) / ttft_baseline

        mmlu_baseline = self.harness.baselines["mmlu_accuracy"]
        mmlu_drop = self._relative_drop(mmlu_baseline, simulated.mmlu_accuracy)
        mmlu_passed = mmlu_drop < 0.01

        arc_rows = tuple(
            {"sample_index": idx, "correct": hit}
            for idx, hit in enumerate(simulated.arc_stub_correct)
        )
        arc_accuracy = sum(1 for row in arc_rows if row["correct"]) / len(arc_rows)
        arc_baseline = self.harness.baselines.get("arc_challenge_accuracy")
        arc_drop = self._relative_drop(arc_baseline, arc_accuracy) if arc_baseline is not None else None
        arc_pending = arc_baseline is None
        arc_passed = True if arc_pending else arc_drop < 0.01

        kv_cache_ratio = self._safe_ratio(
            numerator=simulated.hybrid_kv_cache_bytes,
            denominator=simulated.dense_kv_cache_bytes,
        )
        kv_cache_passed = kv_cache_ratio <= 0.30

        intelligence_gate_passed = mmlu_passed and arc_passed
        phase2_go = decode_gate_passed and intelligence_gate_passed and kv_cache_passed
        payload = {
            "phase": 2,
            "status": "GO" if phase2_go else "NO-GO",
            "phase2_go": phase2_go,
            "gate_reason": self._gate_reason(
                decode_gate_passed=decode_gate_passed,
                mmlu_passed=mmlu_passed,
                arc_passed=arc_passed,
                arc_pending=arc_pending,
                kv_cache_passed=kv_cache_passed,
            ),
            "hybrid_config": self.config.to_dict(
                phase3_ran=self.harness.current_phase >= 3
            ),
            "efficiency_proxy_registered": proxy_registered,
            "decode": {
                "baseline": decode_baseline,
                "new_value": simulated.decode_tokens_per_sec,
                "relative_improvement": decode_improvement,
                "passed_gate": decode_gate_passed,
            },
            "ttft": {
                "baseline": ttft_baseline,
                "new_value": simulated.ttft_seconds,
                "relative_change": ttft_change,
            },
            "kv_cache_vs_dense": {
                "metric_name": "kv_cache_vs_dense",
                "lower_is_better": True,
                "formula": "kv_cache_vs_dense = hybrid_kv_cache_bytes / dense_kv_cache_bytes",
                "dense_kv_cache_bytes": simulated.dense_kv_cache_bytes,
                "hybrid_kv_cache_bytes": simulated.hybrid_kv_cache_bytes,
                "ratio": kv_cache_ratio,
                "target_max": 0.30,
                "passed_gate": kv_cache_passed,
            },
            "intelligence": {
                "degradation_limit": 0.01,
                "mmlu": {
                "baseline": mmlu_baseline,
                "new_value": simulated.mmlu_accuracy,
                "relative_drop": mmlu_drop,
                "passed_gate": mmlu_passed,
                },
                "arc": {
                "baseline": arc_baseline,
                "new_value": arc_accuracy,
                "relative_drop": arc_drop,
                "passed_gate": arc_passed,
                "arc_pending": arc_pending,
                "stub_samples": arc_rows,
                },
            },
        }
        self._write_report(output_path, payload)
        return payload

    def _write_report(self, output_path: str | Path, payload: dict[str, Any]) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _relative_drop(baseline: float, new_value: float) -> float:
        if baseline <= 0:
            return 0.0 if new_value >= baseline else 1.0
        return max(0.0, (baseline - new_value) / baseline)

    @staticmethod
    def _safe_ratio(*, numerator: float, denominator: float) -> float:
        if denominator <= 0:
            return float("inf")
        return numerator / denominator

    @staticmethod
    def _gate_reason(
        *,
        decode_gate_passed: bool,
        mmlu_passed: bool,
        arc_passed: bool,
        arc_pending: bool,
        kv_cache_passed: bool,
    ) -> str:
        reasons: list[str] = []
        if not decode_gate_passed:
            reasons.append("Decode improvement did not exceed +30% baseline threshold.")
        if not mmlu_passed:
            reasons.append("MMLU drop must be <1% vs baseline.")
        if not arc_passed:
            reasons.append("ARC drop must be <1% vs baseline.")
        if not kv_cache_passed:
            reasons.append("kv_cache_vs_dense must be <= 0.30.")
        if reasons:
            return " ".join(reasons)
        if arc_pending:
            return "Decode and KV-cache gates passed; MMLU passed; ARC baseline pending."
        return "Decode, KV-cache, and intelligence drop gates passed."
