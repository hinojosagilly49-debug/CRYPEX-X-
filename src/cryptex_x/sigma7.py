from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Phase1BaselineSpec:
    model_name: str
    model_scale: str
    tokenizer: str
    context_length: int
    training_recipe: str
    eval_prompts: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class BenchmarkSample:
    prompt: str
    expected: str


@dataclass(frozen=True)
class BenchmarkRun:
    name: str
    metric_name: str
    higher_is_better: bool
    aggregate_value: float
    target: float
    passed_target: bool
    raw_outputs: tuple[dict[str, Any], ...]


class Sigma7EvaluationHarness:
    """Strict evaluation engine enforcing BASELINE -> ABLATION -> MEASURE."""

    LOWER_IS_BETTER = {"latency", "memory", "miss_rate"}

    def __init__(self) -> None:
        self.baselines: dict[str, float] = {}
        self.current_phase = 0
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    def register_baseline(self, task: str, metric_name: str, value: float) -> None:
        key = f"{task}_{metric_name}"
        if key in self.baselines:
            raise ValueError(f"Baseline already locked for {key}.")
        self.baselines[key] = value
        logging.info("Locked Baseline | %s %s: %.4f", task, metric_name, value)

    def evaluate_ablation(
        self,
        phase_name: str,
        task: str,
        metric_name: str,
        new_value: float,
        degradation_limit: float = 0.02,
    ) -> bool:
        baseline_key = f"{task}_{metric_name}"
        if baseline_key not in self.baselines:
            raise ValueError(f"No baseline registered for {baseline_key}. Run Phase 1 first.")

        baseline_val = self.baselines[baseline_key]
        change = (new_value - baseline_val) / baseline_val

        logging.info("--- ABLATION TEST: %s ---", phase_name)
        logging.info("Task: %s | Metric: %s", task, metric_name)
        logging.info(
            "Baseline: %.4f | New: %.4f | Change: %.2f%%",
            baseline_val,
            new_value,
            change * 100,
        )

        if metric_name in self.LOWER_IS_BETTER:
            if new_value > baseline_val * (1 + degradation_limit):
                logging.error("[NO-GO] %s rejected. Exceeded degradation limit.", phase_name)
                return False
        else:
            if new_value < baseline_val * (1 - degradation_limit):
                logging.error("[NO-GO] %s rejected. Exceeded degradation limit.", phase_name)
                return False

        logging.info("[GO] %s accepted.", phase_name)
        return True


class Phase1BaselineRunner:
    """Phase 1 baseline simulator with deterministic benchmark scoring."""

    def __init__(
        self,
        *,
        spec: Phase1BaselineSpec,
        harness: Sigma7EvaluationHarness,
        seed: int = 7,
    ) -> None:
        self.spec = spec
        self.harness = harness
        self.seed = seed
        self._benchmarks = self._build_benchmarks()

    def run_and_lock(self, *, report_path: str | Path) -> dict[str, Any]:
        benchmark_runs = [self._run_benchmark(config) for config in self._benchmarks]
        locked = self._lock_phase1_baselines(benchmark_runs)

        phase1_go = len(benchmark_runs) == 3 and locked
        status = "GO" if phase1_go else "NO-GO"
        if phase1_go:
            self.harness.current_phase = max(self.harness.current_phase, 1)

        gate_reason = (
            "All required baselines were produced and locked."
            if phase1_go
            else (
                "Missing benchmark output."
                if len(benchmark_runs) != 3
                else "Baseline lock failed."
            )
        )

        report = {
            "phase": 1,
            "status": status,
            "phase1_go": phase1_go,
            "seed": self.seed,
            "spec": self._spec_to_jsonable(),
            "benchmarks": [asdict(run) for run in benchmark_runs],
            "locked_baselines": dict(self.harness.baselines),
            "gate_reason": gate_reason,
        }
        self._write_report(report_path, report)
        logging.info("Phase 1 completed with status: %s", status)
        return report

    def _lock_phase1_baselines(self, benchmark_runs: list[BenchmarkRun]) -> bool:
        try:
            for run in benchmark_runs:
                self.harness.register_baseline(run.name, run.metric_name, run.aggregate_value)
        except ValueError as exc:
            logging.error("Phase 1 baseline lock failed: %s", exc)
            return False
        return True

    def _build_benchmarks(self) -> tuple[dict[str, Any], ...]:
        return (
            {
                "name": "mmlu",
                "metric_name": "accuracy",
                "higher_is_better": True,
                "target": 0.70,
                "samples": (
                    BenchmarkSample(
                        prompt="A prime number greater than 2 must be?",
                        expected="odd",
                    ),
                    BenchmarkSample(
                        prompt="Water boils at sea level around?",
                        expected="100c",
                    ),
                    BenchmarkSample(
                        prompt="Derivative of x^2 is?",
                        expected="2x",
                    ),
                ),
            },
            {
                "name": "gsm8k",
                "metric_name": "accuracy",
                "higher_is_better": True,
                "target": 0.80,
                "samples": (
                    BenchmarkSample(
                        prompt="If 8 books cost $48, what is one book?",
                        expected="6",
                    ),
                    BenchmarkSample(
                        prompt="Tom has 12 apples, gives away 5, then buys 4. How many now?",
                        expected="11",
                    ),
                    BenchmarkSample(
                        prompt="A train moves 60 km/h for 2 hours. Distance?",
                        expected="120",
                    ),
                ),
            },
            {
                "name": "ruler",
                "metric_name": "miss_rate",
                "higher_is_better": False,
                "target": 0.001,
                "samples": (
                    BenchmarkSample(
                        prompt="retrieve marker token: ALPHA-9241",
                        expected="ALPHA-9241",
                    ),
                    BenchmarkSample(
                        prompt="retrieve marker token: BRAVO-7712",
                        expected="BRAVO-7712",
                    ),
                    BenchmarkSample(
                        prompt="retrieve marker token: CHARLIE-3145",
                        expected="CHARLIE-3145",
                    ),
                ),
            },
        )

    def _run_benchmark(self, config: dict[str, Any]) -> BenchmarkRun:
        samples: tuple[BenchmarkSample, ...] = config["samples"]
        raw_outputs: list[dict[str, Any]] = []
        misses = 0

        for idx, sample in enumerate(samples):
            prediction = self._deterministic_predict(config["name"], sample.prompt, sample.expected, idx)
            exact_match = prediction == sample.expected
            misses += 0 if exact_match else 1
            raw_outputs.append(
                {
                    "sample_index": idx,
                    "prompt": sample.prompt,
                    "expected": sample.expected,
                    "prediction": prediction,
                    "exact_match": exact_match,
                }
            )

        total = len(samples)
        if config["metric_name"] == "miss_rate":
            aggregate_value = misses / total
            passed_target = aggregate_value < config["target"]
        else:
            aggregate_value = (total - misses) / total
            passed_target = aggregate_value > config["target"]

        return BenchmarkRun(
            name=config["name"],
            metric_name=config["metric_name"],
            higher_is_better=config["higher_is_better"],
            aggregate_value=aggregate_value,
            target=config["target"],
            passed_target=passed_target,
            raw_outputs=tuple(raw_outputs),
        )

    def _deterministic_predict(
        self,
        benchmark_name: str,
        prompt: str,
        expected: str,
        idx: int,
    ) -> str:
        msg = f"{self.seed}|{benchmark_name}|{prompt}|{idx}"
        digest = hashlib.sha256(msg.encode("utf-8")).hexdigest()
        if benchmark_name == "ruler":
            return expected if int(digest[-1], 16) > 0 else f"{expected}-MISS"
        return expected if int(digest[-1], 16) > 2 else "incorrect"

    def _write_report(self, report_path: str | Path, report: dict[str, Any]) -> None:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        logging.info("Wrote baseline report artifact: %s", path)

    def _spec_to_jsonable(self) -> dict[str, Any]:
        spec_dict = asdict(self.spec)
        spec_dict["eval_prompts"] = {
            key: list(value) for key, value in spec_dict["eval_prompts"].items()
        }
        return spec_dict


def default_phase1_spec() -> Phase1BaselineSpec:
    return Phase1BaselineSpec(
        model_name="dense-transformer-baseline",
        model_scale="1B",
        tokenizer="cl100k-like",
        context_length=64_000,
        training_recipe="fp16 dense transformer pretrain + supervised eval-only checkpoint",
        eval_prompts={
            "mmlu": (
                "A prime number greater than 2 must be?",
                "Water boils at sea level around?",
                "Derivative of x^2 is?",
            ),
            "gsm8k": (
                "If 8 books cost $48, what is one book?",
                "Tom has 12 apples, gives away 5, then buys 4. How many now?",
                "A train moves 60 km/h for 2 hours. Distance?",
            ),
            "ruler": (
                "retrieve marker token: ALPHA-9241",
                "retrieve marker token: BRAVO-7712",
                "retrieve marker token: CHARLIE-3145",
            ),
        },
    )


def phase1_seed_sweep(
    *,
    start_seed: int = 1,
    end_seed: int = 16,
    report_dir: str | Path = "/tmp",
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    spec = default_phase1_spec()
    report_base = Path(report_dir)
    report_base.mkdir(parents=True, exist_ok=True)
    for seed in range(start_seed, end_seed + 1):
        harness = Sigma7EvaluationHarness()
        runner = Phase1BaselineRunner(spec=spec, harness=harness, seed=seed)
        report = runner.run_and_lock(
            report_path=report_base / f"phase1_seed_{seed}.json"
        )
        aggregates = {
            item["name"]: item["aggregate_value"] for item in report["benchmarks"]
        }
        results.append(
            {
                "seed": seed,
                "status": report["status"],
                "phase1_go": report["phase1_go"],
                "aggregates": aggregates,
                "locked_baselines": report["locked_baselines"],
            }
        )

    return {
        "phase": 1,
        "seed_range": [start_seed, end_seed],
        "results": results,
    }
