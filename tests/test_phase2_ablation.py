from __future__ import annotations

from pathlib import Path

from cryptex_x.arch.hybrid import Phase2AblationRunner, Phase2SimulatedMetrics
from cryptex_x.sigma7 import (
    Phase1BaselineRunner,
    Sigma7EvaluationHarness,
    default_phase1_spec,
)


def _harness_with_phase1_locked(tmp_path: Path) -> Sigma7EvaluationHarness:
    harness = Sigma7EvaluationHarness()
    runner = Phase1BaselineRunner(spec=default_phase1_spec(), harness=harness, seed=7)
    runner.run_and_lock(report_path=tmp_path / "phase1.json")
    return harness


def test_phase2_refuses_without_required_phase1_locks(tmp_path: Path):
    harness = Sigma7EvaluationHarness()
    phase2 = Phase2AblationRunner(harness=harness)
    report = phase2.run(output_path=tmp_path / "phase2_missing.json")

    assert report["status"] == "NO-GO"
    assert report["phase2_go"] is False
    assert set(report["missing_phase1_keys"]) == {
        "mmlu_accuracy",
        "gsm8k_accuracy",
        "ruler_miss_rate",
    }


def test_phase2_registers_efficiency_proxies_once_when_decode_missing(tmp_path: Path):
    harness = _harness_with_phase1_locked(tmp_path)
    phase2 = Phase2AblationRunner(harness=harness)

    report_1 = phase2.run(output_path=tmp_path / "phase2_1.json")
    report_2 = phase2.run(output_path=tmp_path / "phase2_2.json")

    assert report_1["efficiency_proxy_registered"] is True
    assert report_2["efficiency_proxy_registered"] is False
    assert "inference_decode_tokens_per_sec" in harness.baselines
    assert "inference_ttft_seconds" in harness.baselines


def test_phase2_decode_gain_must_exceed_thirty_percent(tmp_path: Path):
    harness = _harness_with_phase1_locked(tmp_path)
    harness.register_baseline("inference", "decode_tokens_per_sec", 40.0)
    harness.register_baseline("inference", "ttft_seconds", 0.46)
    phase2 = Phase2AblationRunner(harness=harness)

    no_go = phase2.run(
        metrics=Phase2SimulatedMetrics(decode_tokens_per_sec=52.0, ttft_seconds=0.45),
        output_path=tmp_path / "phase2_nogo.json",
    )
    assert no_go["status"] == "NO-GO"
    assert no_go["decode"]["passed_gate"] is False

    go = phase2.run(
        metrics=Phase2SimulatedMetrics(
            decode_tokens_per_sec=53.0,
            ttft_seconds=0.45,
            mmlu_accuracy=0.331,
        ),
        output_path=tmp_path / "phase2_go.json",
    )
    assert go["status"] == "GO"
    assert go["decode"]["passed_gate"] is True


def test_phase2_requires_mmlu_drop_strictly_below_one_percent(tmp_path: Path):
    harness = _harness_with_phase1_locked(tmp_path)
    harness.register_baseline("inference", "decode_tokens_per_sec", 40.0)
    harness.register_baseline("inference", "ttft_seconds", 0.46)
    phase2 = Phase2AblationRunner(harness=harness)
    mmlu_baseline = harness.baselines["mmlu_accuracy"]

    report = phase2.run(
        metrics=Phase2SimulatedMetrics(
            decode_tokens_per_sec=53.0,
            ttft_seconds=0.45,
            mmlu_accuracy=mmlu_baseline * 0.99,
        ),
        output_path=tmp_path / "phase2_mmlu_bound.json",
    )
    assert report["status"] == "NO-GO"
    assert report["intelligence"]["mmlu"]["passed_gate"] is False
    assert "MMLU drop must be <1%" in report["gate_reason"]


def test_phase2_sets_arc_pending_when_arc_baseline_missing(tmp_path: Path):
    harness = _harness_with_phase1_locked(tmp_path)
    phase2 = Phase2AblationRunner(harness=harness)

    report = phase2.run(output_path=tmp_path / "phase2_arc_pending.json")
    assert report["status"] == "GO"
    assert report["intelligence"]["arc"]["arc_pending"] is True
    assert report["intelligence"]["arc"]["passed_gate"] is True
    assert len(report["intelligence"]["arc"]["stub_samples"]) == 3


def test_phase2_checks_arc_drop_when_arc_baseline_is_locked(tmp_path: Path):
    harness = _harness_with_phase1_locked(tmp_path)
    harness.register_baseline("arc_challenge", "accuracy", 2 / 3)
    phase2 = Phase2AblationRunner(harness=harness)

    go = phase2.run(
        metrics=Phase2SimulatedMetrics(arc_stub_correct=(True, True, False)),
        output_path=tmp_path / "phase2_arc_go.json",
    )
    assert go["status"] == "GO"
    assert go["intelligence"]["arc"]["arc_pending"] is False
    assert go["intelligence"]["arc"]["passed_gate"] is True

    no_go = phase2.run(
        metrics=Phase2SimulatedMetrics(arc_stub_correct=(True, False, False)),
        output_path=tmp_path / "phase2_arc_nogo.json",
    )
    assert no_go["status"] == "NO-GO"
    assert no_go["intelligence"]["arc"]["passed_gate"] is False
    assert "ARC drop must be <1%" in no_go["gate_reason"]
