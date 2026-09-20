"""CPU-only tests: no model download, benchmark access, or inference."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from activation_continuation_colab.artifacts import (
    ArtifactIntegrityError,
    ArtifactRoots,
    ImmediateTrajectoryCheckpointStore,
    write_public_safe_json,
)
from activation_continuation_colab.benchmark_gate import BenchmarkGateError, verify_benchmark_gate
from activation_continuation_colab.config import load_colab_runtime_config
from activation_continuation_colab.preflight import (
    _REQUIRED_CHECK_NAMES,
    _runtime_pins_check,
    _safe_error,
    run_colab_preflight,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = REPOSITORY_ROOT / "activation_continuation" / "configs" / "colab_runtime.json"


class ColabPortabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_colab_runtime_config(CONFIG_PATH)

    def test_pinned_configuration_preserves_primary_runtime(self) -> None:
        self.assertEqual(self.config.model.repo_id, "Qwen/Qwen3-1.7B")
        self.assertEqual(self.config.model.revision, "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e")
        self.assertTrue(self.config.generation.thinking_mode)
        self.assertEqual(self.config.generation.max_new_tokens, 4096)
        self.assertFalse(self.config.benchmark_gate.default_run_benchmark)

    def test_completed_private_trajectory_is_never_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            roots = ArtifactRoots.from_private_root(Path(directory), self.config.artifacts)
            roots.ensure()
            store = ImmediateTrajectoryCheckpointStore(roots.private_study)
            declaration = store.declare_intent(
                problem_id="synthetic-case-01",
                rollout_seed=17,
            )
            receipt = store.write_completed(
                problem_id="synthetic-case-01",
                rollout_seed=17,
                record={"status": "completed", "synthetic": True},
            )
            self.assertEqual(store.state("synthetic-case-01", 17), "completed")
            self.assertEqual(store.resume_action("synthetic-case-01", 17), "skip_completed")
            self.assertEqual(receipt["intent_id"], "synthetic-case-01--seed-17")
            self.assertEqual(declaration["intent_id"], receipt["intent_id"])
            with self.assertRaises(ArtifactIntegrityError):
                store.write_completed(
                    problem_id="synthetic-case-01",
                    rollout_seed=17,
                    record={"status": "replacement"},
                )

    def test_declaration_survives_disconnect_as_non_regenerable_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            roots = ArtifactRoots.from_private_root(Path(directory), self.config.artifacts)
            roots.ensure()
            initial = ImmediateTrajectoryCheckpointStore(roots.private_study)
            initial.declare_intent(problem_id="synthetic-case-02", rollout_seed=18)

            resumed = ImmediateTrajectoryCheckpointStore(roots.private_study)
            self.assertEqual(resumed.state("synthetic-case-02", 18), "interrupted_unknown")
            self.assertEqual(
                resumed.resume_action("synthetic-case-02", 18),
                "preserve_interrupted_unknown",
            )
            with self.assertRaises(ArtifactIntegrityError):
                resumed.write_completed(
                    problem_id="synthetic-case-02",
                    rollout_seed=18,
                    record={"status": "unsafe replacement"},
                )

    def test_public_safe_writer_rejects_drive_path_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ArtifactIntegrityError):
                write_public_safe_json(
                    Path(directory),
                    "unsafe.json",
                    {"bad": "/content/drive/MyDrive/example"},
                )

    def test_dry_run_reports_every_required_gate_without_model_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_colab_preflight(
                config=self.config,
                private_artifact_root=Path(directory),
                execute_synthetic=False,
            )
            self.assertFalse(report.qualification_passed)
            self.assertEqual(set(_REQUIRED_CHECK_NAMES), set(report.checks))
            self.assertTrue(all(check.status in {"PASS", "FAIL"} for check in report.checks.values()))
            self.assertFalse((Path(directory) / "model_cache").joinpath("Qwen--Qwen3-1.7B").exists())
            self.assertNotIn(str(Path(directory)), json.dumps(report.public_dict()))

    def test_benchmark_gate_rejects_missing_frozen_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(BenchmarkGateError):
                verify_benchmark_gate(
                    config=self.config,
                    public_preflight_report={
                        "qualification_passed": True,
                        "config": {"config_sha256": self.config.fingerprint},
                    },
                    repository_root=Path(directory),
                )

    def test_benchmark_gate_verifies_content_hash_binding_and_tier_estimate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository_root = Path(directory)
            manifest_path = repository_root / self.config.benchmark_gate.manifest_path
            manifest_path.parent.mkdir(parents=True)
            report = {
                "qualification_passed": True,
                "report_id": "qwen3-qualified-report",
                "config": {"config_sha256": self.config.fingerprint},
                "runtime": {"repository_commit": "a" * 40},
            }
            content = {
                "execution_binding": {
                    "config_sha256": self.config.fingerprint,
                    "preflight_report_id": report["report_id"],
                    "repository_commit": report["runtime"]["repository_commit"],
                    "model_revision": self.config.model.revision,
                    "tokenizer_revision": self.config.model.tokenizer_revision,
                },
                "tier_decision": {
                    "tier": "C",
                    "qualification_report_id": report["report_id"],
                    "full_study_cost_estimate": {
                        "projected_total_runtime_seconds": 1.0,
                        "projected_total_private_disk_bytes": 1,
                        "projected_peak_vram_bytes": 1,
                    },
                },
            }
            content["manifest_sha256"] = hashlib.sha256(
                json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            ).hexdigest()
            manifest_path.write_text(json.dumps(content), encoding="utf-8")
            verify_benchmark_gate(
                config=self.config,
                public_preflight_report=report,
                repository_root=repository_root,
            )

            content["tier_decision"]["tier"] = "A"
            manifest_path.write_text(json.dumps(content), encoding="utf-8")
            with self.assertRaises(BenchmarkGateError):
                verify_benchmark_gate(
                    config=self.config,
                    public_preflight_report=report,
                    repository_root=repository_root,
                )

    def test_runtime_pin_mismatch_is_explicitly_rejected(self) -> None:
        runtime = {
            "torch_cuda_build": "12.8",
            "package_versions": dict(self.config.runtime_lock.packages),
        }
        runtime["package_versions"]["torch"] = "wrong-version"
        check = _runtime_pins_check(self.config, runtime)
        self.assertEqual(check.status, "FAIL")
        self.assertIn("package:torch", check.measurements["mismatches"])

    def test_public_error_category_never_copies_a_private_path(self) -> None:
        detail = _safe_error(RuntimeError("/content/drive/MyDrive/private/model"))
        self.assertNotIn("/content", detail)
        self.assertIn("RuntimeError", detail)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
