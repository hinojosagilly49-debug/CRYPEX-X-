from __future__ import annotations

from pathlib import Path

from cryptex_x.arch.latent_router import LatentRouter
from cryptex_x.eval.latent_phase5 import Phase5LatentAblationRunner
from cryptex_x.eval.moe_phase4 import Phase4MoEGateRunner
from cryptex_x.sigma7 import (
    Phase1BaselineRunner,
    Sigma7EvaluationHarness,
    default_phase1_spec,
)


def _phase4_ready_harness(tmp_path: Path) -> Sigma7EvaluationHarness:
    harness = Sigma7EvaluationHarness()
    Phase1BaselineRunner(spec=default_phase1_spec(), harness=harness, seed=7).run_and_lock(
        report_path=tmp_path / "phase1.json"
    )
    Phase4MoEGateRunner(harness=harness).run(output_path=tmp_path / "phase4.json")
    return harness


def test_phase5_entropy_must_not_rise_above_two_percent(tmp_path: Path):
    harness = _phase4_ready_harness(tmp_path)
    runner = Phase5LatentAblationRunner(
        harness=harness,
        router=LatentRouter(d_model=1024, latent_dim=16),
    )

    no_go = runner.run(
        baseline_entropy=2.0,
        latent_entropy=2.05,
        gsm8k_v2_after=harness.baselines["gsm8k_accuracy_v2"],
        output_path=tmp_path / "phase5_entropy_nogo.json",
    )
    assert no_go["status"] == "NO-GO"
    assert no_go["routing_entropy"]["passed_gate"] is False

    go = runner.run(
        baseline_entropy=2.0,
        latent_entropy=2.03,
        gsm8k_v2_after=harness.baselines["gsm8k_accuracy_v2"],
        output_path=tmp_path / "phase5_entropy_go.json",
    )
    assert go["status"] == "GO"
    assert go["routing_entropy"]["passed_gate"] is True


def test_phase5_all_to_all_drop_matches_d_over_l(tmp_path: Path):
    harness = _phase4_ready_harness(tmp_path)
    runner = Phase5LatentAblationRunner(
        harness=harness,
        router=LatentRouter(d_model=768, latent_dim=16),
    )
    report = runner.run(
        baseline_entropy=2.0,
        latent_entropy=2.0,
        active_tokens=128,
        dtype_size=2,
        gsm8k_v2_after=harness.baselines["gsm8k_accuracy_v2"],
        output_path=tmp_path / "phase5_bytes.json",
    )
    assert report["all_to_all_bytes"]["formula"] == "active_tokens * dim * dtype_size"
    assert report["all_to_all_bytes"]["drop_ratio"] == 48.0
    assert report["all_to_all_bytes"]["expected_drop_ratio"] == 48.0
    assert report["all_to_all_bytes"]["drop_matches_d_over_l"] is True


def test_phase5_gsm8k_v2_degradation_limit_is_one_point_five_percent(tmp_path: Path):
    harness = _phase4_ready_harness(tmp_path)
    base = harness.baselines["gsm8k_accuracy_v2"]
    runner = Phase5LatentAblationRunner(
        harness=harness,
        router=LatentRouter(d_model=1024, latent_dim=16),
    )

    no_go = runner.run(
        baseline_entropy=2.0,
        latent_entropy=2.0,
        gsm8k_v2_after=base * 0.98,
        output_path=tmp_path / "phase5_gsm8k_nogo.json",
    )
    assert no_go["status"] == "NO-GO"
    assert no_go["gsm8k_v2_ablation"]["passed_gate"] is False

    go = runner.run(
        baseline_entropy=2.0,
        latent_entropy=2.0,
        gsm8k_v2_after=base * 0.986,
        output_path=tmp_path / "phase5_gsm8k_go.json",
    )
    assert go["status"] == "GO"
    assert go["gsm8k_v2_ablation"]["passed_gate"] is True
