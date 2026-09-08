from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from cryptex_x.sigma7 import phase1_seed_sweep


ROOT = Path(__file__).resolve().parents[1]


def test_phase1_seed_sweep_range_and_seed7_pin(tmp_path: Path):
    sweep = phase1_seed_sweep(start_seed=1, end_seed=16, report_dir=tmp_path)

    assert sweep["seed_range"] == [1, 16]
    seeds = [entry["seed"] for entry in sweep["results"]]
    assert seeds == list(range(1, 17))

    seed7 = next(entry for entry in sweep["results"] if entry["seed"] == 7)
    assert seed7["aggregates"]["mmlu"] == 1 / 3
    assert seed7["aggregates"]["gsm8k"] == 1.0
    assert seed7["aggregates"]["ruler"] == 1 / 3


def test_phase1_seed_sweep_script_writes_artifact(tmp_path: Path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    path = ROOT / "artifacts" / "phase1_seed_sweep.json"
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "phase1_seed_sweep.py")],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["seed_range"] == [1, 16]
        assert len(data["results"]) == 16
    finally:
        if path.exists():
            path.unlink()
