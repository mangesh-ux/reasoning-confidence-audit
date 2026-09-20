from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from activation_continuation.runtime_qualification.harness import (
    RuntimeQualificationHarness,
    inspect_activation_artifact,
)
from activation_continuation.runtime_qualification.models import (
    ActivationVector,
    CudaAvailability,
    MemorySnapshot,
    QualificationIntent,
    QualificationPlan,
    SyntheticCase,
    SyntheticExecution,
    planned_intents,
)


class FakeMemoryProbe:
    def __init__(self, *, cuda_available: bool = True) -> None:
        self.cuda_available = cuda_available
        self.reset_calls = 0
        self.snapshot_calls = 0

    def availability(self) -> CudaAvailability:
        return CudaAvailability(
            torch_available=True,
            cuda_available=self.cuda_available,
            device_count=1 if self.cuda_available else 0,
            device_name="fake-gpu" if self.cuda_available else None,
            cuda_version="fake-cuda" if self.cuda_available else None,
            reason=None if self.cuda_available else "fake CUDA disabled",
        )

    def reset_peak(self) -> None:
        self.reset_calls += 1

    def snapshot(self) -> MemorySnapshot:
        self.snapshot_calls += 1
        value = 16 * 1024 * 1024
        return MemorySnapshot(
            cuda_available=self.cuda_available,
            device="cuda",
            allocated_bytes=value if self.cuda_available else None,
            reserved_bytes=value if self.cuda_available else None,
            peak_allocated_bytes=value if self.cuda_available else None,
            free_bytes=64 * value if self.cuda_available else None,
            total_bytes=65 * value if self.cuda_available else None,
        )


class FakeRunner:
    def __init__(self, *, failures: set[str] | None = None) -> None:
        self.failures = failures or set()
        self.prepare_calls = 0
        self.execute_calls: list[str] = []
        self.close_calls = 0

    def prepare(self, plan: QualificationPlan) -> Mapping[str, Any]:
        self.prepare_calls += 1
        return {"runner": "fake", "model_revision": plan.model_revision}

    def execute(
        self, intent: QualificationIntent, plan: QualificationPlan
    ) -> SyntheticExecution:
        self.execute_calls.append(intent.intent_id)
        if intent.intent_id in self.failures:
            raise RuntimeError("preserved fake execution failure")
        return SyntheticExecution(
            prompt_token_count=12,
            generated_token_ids=(101, 102, 103, 104),
            generated_text_sha256=hashlib.sha256(intent.intent_id.encode("utf-8")).hexdigest(),
            elapsed_seconds=2.0,
            context_limit_tokens=8192,
            activations=(
                ActivationVector(layer_index=0, values=(0.25, -0.5), source_dtype="bfloat16"),
                ActivationVector(layer_index=1, values=(1.0, 0.0), source_dtype="bfloat16"),
            ),
            runner_provenance={"fake_seed": intent.seed},
        )

    def close(self) -> None:
        self.close_calls += 1


def make_plan() -> QualificationPlan:
    return QualificationPlan(
        run_id="mock-runtime-qualification",
        model_id="Qwen/Qwen3-1.7B",
        model_revision="pinned-model-revision",
        tokenizer_revision="pinned-tokenizer-revision",
        synthetic_cases=(
            SyntheticCase(
                case_id="mock_synthetic",
                user_prompt="Synthetic prompt only.",
                reasoning_prefix="Synthetic prefix.",
                seed=7,
            ),
        ),
        cycles_per_case=2,
    )


class RuntimeQualificationHarnessTests(unittest.TestCase):
    def test_default_dry_run_never_prepares_or_executes_a_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = FakeRunner()
            harness = RuntimeQualificationHarness(
                output_dir=Path(temporary),
                plan=make_plan(),
                memory_probe=FakeMemoryProbe(),
                runner=runner,
            )
            report = harness.run()

            self.assertEqual(report.execution_status, "dry_run_no_model_calls")
            self.assertEqual(runner.prepare_calls, 0)
            self.assertEqual(runner.execute_calls, [])
            self.assertTrue((Path(temporary) / "qualification_plan.json").exists())

    def test_mock_execution_collects_runtime_and_serialization_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            runner = FakeRunner()
            harness = RuntimeQualificationHarness(
                output_dir=output_dir,
                plan=make_plan(),
                memory_probe=FakeMemoryProbe(),
                runner=runner,
            )
            report = harness.run(execute_synthetic=True)

            self.assertEqual(report.execution_status, "synthetic_execution_finished")
            self.assertEqual(len(runner.execute_calls), 2)
            self.assertEqual(report.summary["completed_intent_count"], 2)
            self.assertEqual(report.summary["aggregate_tokens_per_second"], 2.0)
            self.assertEqual(report.summary["generation_cap_tokens"], 4096)
            self.assertFalse(report.summary["all_cycles_reached_generation_cap"])
            self.assertEqual(report.summary["context_safety_status"], "all_recorded_cycles_safe")
            self.assertEqual(report.summary["memory_stability"]["status"], "within_tolerance")
            artifact = next((output_dir / "activations").rglob("*.acrq"))
            inspected = inspect_activation_artifact(artifact)
            self.assertEqual(inspected["header"]["stored_dtype"], "float16")
            self.assertEqual(inspected["header"]["vector_length"], 2)

    def test_frozen_synthetic_plan_forces_the_full_generation_ceiling(self) -> None:
        plan = make_plan()
        self.assertEqual(plan.generation.min_new_tokens, 4096)
        self.assertEqual(plan.generation.max_new_tokens, 4096)

    def test_completed_failed_and_ambiguous_intents_are_never_automatically_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            plan = make_plan()
            first, second = planned_intents(plan)
            # Simulate a process death after it had declared the first attempt.
            initial = RuntimeQualificationHarness(
                output_dir=output_dir,
                plan=plan,
                memory_probe=FakeMemoryProbe(),
                runner=FakeRunner(),
            )
            initial.run()
            initial.ledger.append(
                "intent_declared",
                plan_fingerprint=plan.fingerprint,
                intent_id=first.intent_id,
                payload={"seed": first.seed},
            )
            runner = FakeRunner(failures={second.intent_id})
            resumed = RuntimeQualificationHarness(
                output_dir=output_dir,
                plan=plan,
                memory_probe=FakeMemoryProbe(),
                runner=runner,
            )
            resumed.run(execute_synthetic=True)
            self.assertEqual(runner.execute_calls, [second.intent_id])

            # A second resume must not execute either the ambiguous first intent
            # or the failed second intent.
            second_runner = FakeRunner()
            resumed_again = RuntimeQualificationHarness(
                output_dir=output_dir,
                plan=plan,
                memory_probe=FakeMemoryProbe(),
                runner=second_runner,
            )
            report = resumed_again.run(execute_synthetic=True)
            self.assertEqual(second_runner.execute_calls, [])
            decisions = {decision.intent_id: decision.action for decision in report.decisions}
            self.assertEqual(decisions[first.intent_id], "preserve_interrupted_unknown")
            self.assertEqual(decisions[second.intent_id], "skip_failed")

    def test_cuda_unavailable_blocks_before_runner_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = FakeRunner()
            harness = RuntimeQualificationHarness(
                output_dir=Path(temporary),
                plan=make_plan(),
                memory_probe=FakeMemoryProbe(cuda_available=False),
                runner=runner,
            )
            report = harness.run(execute_synthetic=True)
            self.assertEqual(report.execution_status, "blocked_cuda_unavailable")
            self.assertEqual(runner.prepare_calls, 0)


if __name__ == "__main__":
    unittest.main()
