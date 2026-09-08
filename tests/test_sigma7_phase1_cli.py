from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _run_cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    return subprocess.run(
        [sys.executable, "-m", "cryptex_x.sigma7_phase1", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_sigma7_phase1_cli_go_writes_artifact_and_prints_three_keys(tmp_path: Path):
    proc = _run_cli(tmp_path)
    assert proc.returncode == 0

    report_path = tmp_path / "artifacts" / "phase1_baseline_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "GO"

    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    assert lines == [
        "mmlu_accuracy=0.3333",
        "gsm8k_accuracy=1.0000",
        "ruler_miss_rate=0.3333",
    ]


def test_sigma7_phase1_cli_nogo_exits_2_when_mmlu_prelocked(tmp_path: Path):
    proc = _run_cli(tmp_path, "--prelock-mmlu-value", "0.99")
    assert proc.returncode == 2

    report_path = tmp_path / "artifacts" / "phase1_baseline_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "NO-GO"
    assert "lock failed" in report["gate_reason"].lower()
