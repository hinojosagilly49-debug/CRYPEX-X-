from __future__ import annotations

import pytest

from pathlib import Path

from cryptex_x.arch.moe import MoEConfig
from cryptex_x.eval.moe_phase4 import GSM8K_V2_SAMPLES, Phase4MoEGateRunner
from cryptex_x.sigma7 import (
    Phase1BaselineRunner,
    Sigma7EvaluationHarness,
    default_phase1_spec,
)


def _phase1_harness(tmp_path: Path) -> Sigma7EvaluationHarness:
    harness = Sigma7EvaluationHarness()
    Phase1BaselineRunner(spec=default_phase1_spec(), harness=harness, seed=7).run_and_lock(
        report_path=tmp_path / "phase1_for_moe.json"
    )
    return harness


def test_moe_config_defaults_and_active_flops_invariant():
    cfg = MoEConfig()
    payload = cfg.to_dict()
    assert cfg.n_experts == 8
    assert cfg.top_k == 1
    assert cfg.active_flops_ratio == 1.0
    assert payload["active_flops_invariant"] == "1.0±1e-6"

    MoEConfig(active_flops_ratio=1.0 + 1e-7).validate()
    with pytest.raises(ValueError):
        MoEConfig(active_flops_ratio=1.0 + 2e-6).validate()


def test_phase4_uses_gsm8k_v2_key_and_keeps_v1_immutable(tmp_path):
    harness = _phase1_harness(tmp_path)
    baseline_v1 = harness.baselines["gsm8k_accuracy"]
    runner = Phase4MoEGateRunner(harness=harness)

    report = runner.run(
        moe_gsm8k_accuracy_v2=0.72,
        output_path=tmp_path / "phase4.json",
    )
    assert len(report["gsm8k_v2"]["samples"]) == 3
    assert [row["prompt"] for row in report["gsm8k_v2"]["samples"]] == [
        sample.prompt for sample in GSM8K_V2_SAMPLES
    ]
    assert "gsm8k_accuracy_v2" in harness.baselines
    assert harness.baselines["gsm8k_accuracy"] == baseline_v1
    assert report["baseline_integrity"]["gsm8k_v1_unchanged"] is True


def test_phase4_requires_strict_plus_five_percent_over_locked_v2(tmp_path):
    harness = _phase1_harness(tmp_path)
    harness.register_baseline("gsm8k_accuracy", "v2", 2 / 3)
    baseline_v1 = harness.baselines["gsm8k_accuracy"]
    runner = Phase4MoEGateRunner(harness=harness)

    no_go = runner.run(
        moe_gsm8k_accuracy_v2=0.70,
        output_path=tmp_path / "phase4_nogo.json",
    )
    assert no_go["status"] == "NO-GO"
    assert no_go["gsm8k_v2"]["passed_gate"] is False
    assert no_go["gsm8k_v2"]["relative_gain"] == pytest.approx(0.05, abs=1e-12)
    assert harness.baselines["gsm8k_accuracy"] == baseline_v1

    go = runner.run(
        moe_gsm8k_accuracy_v2=0.71,
        output_path=tmp_path / "phase4_go.json",
    )
    assert go["status"] == "GO"
    assert go["gsm8k_v2"]["passed_gate"] is True
    assert go["gsm8k_v2"]["relative_gain"] > 0.05
    assert harness.baselines["gsm8k_accuracy"] == baseline_v1
