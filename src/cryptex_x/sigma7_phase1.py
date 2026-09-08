from __future__ import annotations

import argparse
from pathlib import Path

from .sigma7 import Phase1BaselineRunner, Sigma7EvaluationHarness, default_phase1_spec


REPORT_PATH = Path("artifacts/phase1_baseline_report.json")
LOCKED_KEYS = ("mmlu_accuracy", "gsm8k_accuracy", "ruler_miss_rate")


def run_phase1_cli(prelock_mmlu_value: float | None = None) -> int:
    harness = Sigma7EvaluationHarness()
    if prelock_mmlu_value is not None:
        harness.register_baseline("mmlu", "accuracy", prelock_mmlu_value)

    runner = Phase1BaselineRunner(spec=default_phase1_spec(), harness=harness, seed=7)
    runner.run_and_lock(report_path=REPORT_PATH)

    for key in LOCKED_KEYS:
        if key in harness.baselines:
            print(f"{key}={harness.baselines[key]:.4f}")

    return 0 if all(key in harness.baselines for key in LOCKED_KEYS) else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Sigma7 Phase 1 baseline lock.")
    parser.add_argument(
        "--prelock-mmlu-value",
        type=float,
        default=None,
        help="Pre-register mmlu_accuracy to force NO-GO lock failure path.",
    )
    args = parser.parse_args()
    return run_phase1_cli(prelock_mmlu_value=args.prelock_mmlu_value)


if __name__ == "__main__":
    raise SystemExit(main())
