from __future__ import annotations

import hashlib
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


def test_seed_7_reproduces_official_phase1_scores(tmp_path: Path):
    runner = Phase1BaselineRunner(
        spec=default_phase1_spec(),
        harness=Sigma7EvaluationHarness(),
        seed=7,
    )
    report = runner.run_and_lock(report_path=tmp_path / "seed7.json")
    aggregates = {item["name"]: item["aggregate_value"] for item in report["benchmarks"]}

    assert aggregates["mmlu"] == pytest.approx(1 / 3, abs=1e-12)
    assert aggregates["gsm8k"] == pytest.approx(1.0, abs=1e-12)
    assert aggregates["ruler"] == pytest.approx(1 / 3, abs=1e-12)


def test_deterministic_predict_threshold_rules():
    runner = Phase1BaselineRunner(
        spec=default_phase1_spec(),
        harness=Sigma7EvaluationHarness(),
        seed=7,
    )

    def _find_prompt(bench: str, idx: int, want) -> str:
        for n in range(2000):
            prompt = f"probe-{bench}-{idx}-{n}"
            digest = hashlib.sha256(
                f"{runner.seed}|{bench}|{prompt}|{idx}".encode("utf-8")
            ).hexdigest()
            if want(int(digest[-1], 16)):
                return prompt
        raise AssertionError("Unable to find matching prompt for threshold probe")

    ruler_miss_prompt = _find_prompt("ruler", 0, lambda nibble: nibble == 0)
    ruler_hit_prompt = _find_prompt("ruler", 1, lambda nibble: nibble > 0)
    generic_miss_prompt = _find_prompt("mmlu", 0, lambda nibble: nibble <= 2)
    generic_hit_prompt = _find_prompt("mmlu", 1, lambda nibble: nibble > 2)

    assert (
        runner._deterministic_predict("ruler", ruler_miss_prompt, "ALPHA-9241", 0)
        == "ALPHA-9241-MISS"
    )
    assert (
        runner._deterministic_predict("ruler", ruler_hit_prompt, "BRAVO-7712", 1)
        == "BRAVO-7712"
    )
    assert (
        runner._deterministic_predict("mmlu", generic_miss_prompt, "odd", 0)
        == "incorrect"
    )
    assert (
        runner._deterministic_predict("mmlu", generic_hit_prompt, "odd", 1)
        == "odd"
    )


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
