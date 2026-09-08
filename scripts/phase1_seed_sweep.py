#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from cryptex_x.sigma7 import phase1_seed_sweep


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "phase1_seed_sweep.json"


def main() -> None:
    sweep = phase1_seed_sweep(start_seed=1, end_seed=16)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sweep, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
