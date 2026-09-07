from __future__ import annotations

import json
from pathlib import Path

import pytest

from cryptex_x import (
    Phase1BaselineRunner,
    Sigma7EvaluationHarness,
    default_phase1_spec,
)


def test_phase1_runner_locks_three_baselines_and_writes_artifact(tmp_path: Path):
    harness = Sigma7EvaluationHarness()
    runner = Phase1BaselineRunner(spec=default_phase1_spec(), harness=harness, seed=7)
    report_path = tmp_path / "artifacts" / "phase1_baseline_report.json"

    report = runner.run_and_lock(report_path=report_path)

    assert report["phase"] == 1
    assert report["phase1_go"] is True
    assert report["status"] == "GO"
    assert set(harness.baselines.keys()) == {
        "mmlu_accuracy",
        "gsm8k_accuracy",
        "ruler_miss_rate",
    }
    on_disk = json.loads(report_path.read_text(encoding="utf-8"))
    assert on_disk["locked_baselines"] == report["locked_baselines"]


def test_phase1_runner_is_deterministic_for_same_seed(tmp_path: Path):
    spec = default_phase1_spec()
    runner_a = Phase1BaselineRunner(spec=spec, harness=Sigma7EvaluationHarness(), seed=7)
    runner_b = Phase1BaselineRunner(spec=spec, harness=Sigma7EvaluationHarness(), seed=7)

    report_a = runner_a.run_and_lock(report_path=tmp_path / "a.json")
    report_b = runner_b.run_and_lock(report_path=tmp_path / "b.json")

    agg_a = {item["name"]: item["aggregate_value"] for item in report_a["benchmarks"]}
    agg_b = {item["name"]: item["aggregate_value"] for item in report_b["benchmarks"]}
    assert agg_a == agg_b


def test_phase1_runner_blocks_phase2_when_lock_fails(tmp_path: Path):
    harness = Sigma7EvaluationHarness()
    harness.register_baseline("mmlu", "accuracy", 0.99)
    runner = Phase1BaselineRunner(spec=default_phase1_spec(), harness=harness, seed=7)

    report = runner.run_and_lock(report_path=tmp_path / "phase1_fail.json")

    assert report["phase1_go"] is False
    assert report["status"] == "NO-GO"
    assert "lock failed" in report["gate_reason"].lower()


def test_baselines_are_immutable_once_locked():
    harness = Sigma7EvaluationHarness()
    harness.register_baseline("mmlu", "accuracy", 0.71)

    with pytest.raises(ValueError):
        harness.register_baseline("mmlu", "accuracy", 0.75)
