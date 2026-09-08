from __future__ import annotations

from pathlib import Path

from cryptex_x.eval.mrcr_v2 import Phase3MrcrV2Runner
from cryptex_x.sigma7 import Sigma7EvaluationHarness


def test_mrcr_v2_locks_baseline_only_when_absent(tmp_path: Path):
    harness = Sigma7EvaluationHarness()
    runner = Phase3MrcrV2Runner(harness=harness, seed=7)
    report = runner.run(output_path=tmp_path / "phase3_mrcr.json")

    assert report["benchmark"] == "mrcr_v2"
    assert len(report["rows"]) == 3
    assert report["target_accuracy"] == 0.70
    assert report["locked_new_baseline"] is True
    assert "mrcr_accuracy" in harness.baselines
    assert harness.baselines["mrcr_accuracy"] == report["accuracy"]

    locked_value = harness.baselines["mrcr_accuracy"]
    again = runner.run(output_path=tmp_path / "phase3_mrcr_again.json")
    assert again["locked_new_baseline"] is False
    assert harness.baselines["mrcr_accuracy"] == locked_value


def test_mrcr_v2_respects_prelocked_baseline_value(tmp_path: Path):
    harness = Sigma7EvaluationHarness()
    harness.register_baseline("mrcr", "accuracy", 0.99)
    runner = Phase3MrcrV2Runner(harness=harness, seed=7)
    report = runner.run(output_path=tmp_path / "phase3_mrcr_prelocked.json")

    assert report["locked_new_baseline"] is False
    assert report["baseline_before"] == 0.99
    assert report["baseline_after"] == 0.99
    assert harness.baselines["mrcr_accuracy"] == 0.99
