from __future__ import annotations

import json

import pytest

from cryptex_x.arch.latent_router import LatentRouter, serialize_phase5_latent_router


def test_latent_router_records_reduction_ratio():
    router = LatentRouter(d_model=1024, latent_dim=16)
    payload = router.to_dict()
    assert payload["reduction_ratio"] == 64.0
    assert payload["reduction_formula"] == "d_model / latent_dim"


def test_latent_router_requires_latent_dim_smaller_than_d_model():
    with pytest.raises(ValueError):
        LatentRouter(d_model=16, latent_dim=16)


def test_phase5_latent_router_serialization(tmp_path):
    out = tmp_path / "artifacts" / "phase5_latent_router.json"
    payload = serialize_phase5_latent_router(
        LatentRouter(d_model=768, latent_dim=16),
        output_path=out,
    )
    assert out.exists()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == payload
    assert payload["latent_router"]["reduction_ratio"] == 48.0
