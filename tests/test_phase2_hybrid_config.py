from __future__ import annotations

import json
from pathlib import Path

from cryptex_x.arch.hybrid import HybridConfig, serialize_phase2_hybrid_config


def test_hybrid_config_defaults_to_1_over_8_global_attention():
    cfg = HybridConfig()
    data = cfg.to_dict()

    assert cfg.attn_every == 8
    assert cfg.ssm == "mamba2"
    assert data["global_attention_ratio"] == "1/8"
    assert data["global_attention_fraction"] == 0.125


def test_phase2_hybrid_config_serialization_writes_artifact(tmp_path: Path):
    out = tmp_path / "artifacts" / "phase2_hybrid_config.json"
    payload = serialize_phase2_hybrid_config(output_path=out)

    assert out.exists()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == payload
    assert payload["phase"] == 2
    assert payload["hybrid_config"]["attn_every"] == 8
    assert payload["hybrid_config"]["ssm"] == "mamba2"
