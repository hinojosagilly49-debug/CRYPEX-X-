from __future__ import annotations

import json
from pathlib import Path

from cryptex_x.arch.hybrid import HybridConfig, serialize_phase2_hybrid_config
from cryptex_x.eval.ruler64k import Phase3Ruler64kProtocolRunner
from cryptex_x.sigma7 import (
    Phase1BaselineRunner,
    Sigma7EvaluationHarness,
    default_phase1_spec,
)


def test_hybrid_config_defaults_to_1_over_8_global_attention():
    cfg = HybridConfig()
    data = cfg.to_dict()

    assert cfg.attn_every == 8
    assert cfg.ssm == "mamba2"
    assert data["global_attention_ratio"] == "1/8"
    assert data["global_attention_fraction"] == 0.125
    assert data["phase3_context_validated"] is False
    assert data["advertised_context_length"] == 8192


def test_phase2_hybrid_config_serialization_writes_artifact(tmp_path: Path):
    out = tmp_path / "artifacts" / "phase2_hybrid_config.json"
    payload = serialize_phase2_hybrid_config(output_path=out)

    assert out.exists()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == payload
    assert payload["phase"] == 2
    assert payload["hybrid_config"]["attn_every"] == 8
    assert payload["hybrid_config"]["ssm"] == "mamba2"
    assert payload["hybrid_config"]["advertised_context_length"] == 8192


def test_hybrid_may_advertise_64k_only_after_phase3_ran(tmp_path: Path):
    harness = Sigma7EvaluationHarness()
    Phase1BaselineRunner(spec=default_phase1_spec(), harness=harness, seed=7).run_and_lock(
        report_path=tmp_path / "phase1.json"
    )
    cfg = HybridConfig()
    pre_phase3 = cfg.to_dict(phase3_ran=harness.current_phase >= 3)
    assert pre_phase3["advertised_context_length"] == 8192

    Phase3Ruler64kProtocolRunner(harness=harness).run(output_path=tmp_path / "phase3.json")
    post_phase3 = cfg.to_dict(phase3_ran=harness.current_phase >= 3)
    assert post_phase3["advertised_context_length"] == 64000
    assert post_phase3["phase3_context_validated"] is True
