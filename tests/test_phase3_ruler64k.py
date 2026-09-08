from __future__ import annotations

from pathlib import Path

from cryptex_x.eval.ruler64k import PHASE3_RULER_MARKERS, Phase3Ruler64kProtocolRunner
from cryptex_x.sigma7 import (
    Phase1BaselineRunner,
    Sigma7EvaluationHarness,
    default_phase1_spec,
)


def _phase1_harness(tmp_path: Path) -> Sigma7EvaluationHarness:
    harness = Sigma7EvaluationHarness()
    Phase1BaselineRunner(spec=default_phase1_spec(), harness=harness, seed=7).run_and_lock(
        report_path=tmp_path / "phase1.json"
    )
    return harness


def test_phase3_uses_official_markers_and_fraction_unit(tmp_path: Path):
    harness = _phase1_harness(tmp_path)
    runner = Phase3Ruler64kProtocolRunner(harness=harness)
    report = runner.run(output_path=tmp_path / "phase3.json")

    assert report["ruler"]["markers"] == list(PHASE3_RULER_MARKERS)
    assert report["ruler"]["formula"] == "miss_rate_fraction = misses / n"
    assert "target_max_fraction" in report["ruler"]
    assert "miss_rate_fraction" in report["ruler"]
    assert report["context_protocol"]["context_length_tokens"] == 64000
    assert report["context_protocol"]["full_context_payload_stored"] is False


def test_phase3_strict_threshold_and_no_baseline_rewrite(tmp_path: Path):
    harness = _phase1_harness(tmp_path)
    locked_before = harness.baselines["ruler_miss_rate"]
    runner = Phase3Ruler64kProtocolRunner(harness=harness)

    no_go = runner.run(
        predictions=("ALPHA-9241", "BRAVO-7712", "CHARLIE-3145-MISS"),
        output_path=tmp_path / "phase3_nogo.json",
    )
    assert no_go["status"] == "NO-GO"
    assert no_go["phase3_go"] is False
    assert no_go["ruler"]["miss_rate_fraction"] == 1 / 3
    assert no_go["ruler"]["passed_gate"] is False
    assert no_go["ruler"]["verbatim_misses"] == ["CHARLIE-3145"]
    assert no_go["gate_reason"] == "RULER miss rate must be < 0.001 (fraction)."
    assert harness.baselines["ruler_miss_rate"] == locked_before

    go = runner.run(
        predictions=PHASE3_RULER_MARKERS,
        output_path=tmp_path / "phase3_go.json",
    )
    assert go["status"] == "GO"
    assert go["ruler"]["miss_rate_fraction"] == 0.0
    assert go["ruler"]["passed_gate"] is True
    assert go["ruler"]["verbatim_misses"] == []
    assert harness.baselines["ruler_miss_rate"] == locked_before


def test_phase3_requires_locked_ruler_baseline(tmp_path: Path):
    harness = Sigma7EvaluationHarness()
    runner = Phase3Ruler64kProtocolRunner(harness=harness)
    report = runner.run(output_path=tmp_path / "phase3_missing.json")

    assert report["status"] == "NO-GO"
    assert report["missing_phase1_keys"] == ["ruler_miss_rate"]
