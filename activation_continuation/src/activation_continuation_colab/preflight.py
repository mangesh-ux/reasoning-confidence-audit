"""Explicit Colab GPU qualification gate for the frozen activation study.

This module contains execution plumbing only. It does not construct a study
manifest, select benchmark rows, or invoke benchmark generation. The one
optional model execution is the predeclared synthetic runtime qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from activation_continuation.runtime_qualification.harness import (
    RuntimeQualificationHarness,
    inspect_activation_artifact,
)
from activation_continuation.runtime_qualification.models import GenerationSpec, QualificationPlan
from activation_continuation.runtime_qualification.runner import (
    NativeTransformersBf16Qwen3Runner,
    TorchCudaMemoryProbe,
)

from .artifacts import ArtifactRoots, write_public_safe_json
from .config import ColabRuntimeConfig, load_colab_runtime_config
from .model_snapshot import retrieve_and_verify_pinned_model


PASS = "PASS"
FAIL = "FAIL"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    measurements: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.status not in {PASS, FAIL}:
            raise ValueError("preflight checks must use explicit PASS or FAIL")

    def public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "detail": self.detail,
            "measurements": dict(self.measurements),
        }


@dataclass(frozen=True)
class ColabPreflightReport:
    report_id: str
    qualification_passed: bool
    checks: Mapping[str, Check]
    runtime: Mapping[str, object]
    config_identity: Mapping[str, object]
    qualification_summary: Mapping[str, object] | None
    public_report_filename: str

    def public_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "report_id": self.report_id,
            "qualification_passed": self.qualification_passed,
            "checks": {name: check.public_dict() for name, check in self.checks.items()},
            "runtime": dict(self.runtime),
            "config": dict(self.config_identity),
            "qualification_summary": (
                dict(self.qualification_summary) if self.qualification_summary is not None else None
            ),
            "artifact_layout": {
                "repository": "repository checkout (code/config/manifests only)",
                "private": "Drive-backed runtime artifacts are intentionally omitted",
                "public_safe": "aggregate path-free report only",
            },
        }


def run_colab_preflight(
    *,
    config: ColabRuntimeConfig,
    private_artifact_root: Path,
    execute_synthetic: bool,
) -> ColabPreflightReport:
    """Run the requested qualification and produce a path-free PASS/FAIL report.

    The call stops before any benchmark manifest or benchmark runner. A failed
    prerequisite also prevents model retrieval, so unsuitable Colab hardware
    does not create an unnecessary Drive model cache.
    """

    roots = ArtifactRoots.from_private_root(private_artifact_root, config.artifacts)
    roots.ensure()
    report_id = _report_id(config)
    checks, runtime, torch_module = _environment_checks(config, roots, report_id)
    checks["evaluator_fixtures"] = _evaluator_fixture_check(config, roots, report_id)
    qualification_summary: Mapping[str, object] | None = None

    prerequisites = (
        checks["runtime_pins"].status == PASS
        and checks["cuda_available"].status == PASS
        and checks["device_name"].status == PASS
        and checks["vram"].status == PASS
        and checks["bf16_runtime_suitability"].status == PASS
        and checks["disk_availability"].status == PASS
        and checks["evaluator_fixtures"].status == PASS
        and execute_synthetic
    )
    if not execute_synthetic:
        _set_dependent_failures(
            checks,
            "synthetic qualification was not explicitly requested; model and benchmark execution are blocked",
        )
    elif not prerequisites:
        _set_dependent_failures(
            checks,
            "one or more runtime-version, evaluator, CUDA/BF16, or disk prerequisites failed; model and benchmark execution are blocked",
        )
    else:
        assert torch_module is not None
        try:
            execution_identity = _qualification_execution_identity(config, runtime)
            plan = _qualification_plan(config)
            execution_identity_sha256 = _execution_identity_sha256(execution_identity)
            run_directory = roots.qualification / (
                f"{plan.run_id}-{plan.fingerprint[:12]}-{execution_identity_sha256[:12]}"
            )
            execution_identity_sha256 = _freeze_or_validate_execution_identity(
                run_directory, execution_identity
            )
            runtime["qualification_execution_identity_sha256"] = execution_identity_sha256
            checks["qualification_provenance"] = Check(
                "qualification_provenance",
                PASS,
                "qualification evidence is bound to the checked-out source, pinned runtime, and GPU identity",
                {"execution_identity_sha256": execution_identity_sha256},
            )
        except Exception as error:
            _write_private_diagnostic(roots, report_id, "qualification_provenance", error)
            checks["qualification_provenance"] = Check(
                "qualification_provenance", FAIL, _safe_error(error), {}
            )
            _set_dependent_failures(
                checks,
                "qualification provenance could not be frozen; model and benchmark execution are blocked",
            )
        else:
            try:
                snapshot = retrieve_and_verify_pinned_model(config.model, roots)
                runtime["model_snapshot"] = snapshot.public_dict()
                checks["model_retrieval"] = Check(
                    "model_retrieval",
                    PASS,
                    "pinned Hub revision was resolved and retrieved into private storage",
                    {
                        "requested_revision": config.model.revision,
                        "resolved_revision": snapshot.resolved_revision,
                        "metadata_file_count": len(snapshot.metadata_file_sha256),
                    },
                )
            except Exception as error:
                _write_private_diagnostic(roots, report_id, "model_retrieval", error)
                checks["model_retrieval"] = Check(
                    "model_retrieval", FAIL, _safe_error(error), {}
                )
                _set_dependent_failures(
                    checks,
                    "pinned model retrieval/verification failed; qualification and benchmark execution are blocked",
                )
            else:
                try:
                    harness = RuntimeQualificationHarness(
                        output_dir=run_directory,
                        plan=plan,
                        memory_probe=TorchCudaMemoryProbe(),
                        runner=NativeTransformersBf16Qwen3Runner(
                            model_source=str(snapshot.local_path)
                        ),
                    )
                    initial = harness.run(execute_synthetic=True)
                    qualification_summary = initial.summary
                    ledger_records = harness.ledger.read()
                    checks["model_load"] = _model_load_check(ledger_records)
                    checks["hidden_state_extraction"] = _activation_check(
                        ledger_records=ledger_records,
                        qualification_output=run_directory,
                        diagnostic_recorder=lambda phase, error: _write_private_diagnostic(
                            roots, report_id, phase, error
                        ),
                    )
                    checks["repeated_generation_soak"] = _soak_check(initial)
                    if (
                        checks["model_load"].status == PASS
                        and checks["hidden_state_extraction"].status == PASS
                        and checks["repeated_generation_soak"].status == PASS
                    ):
                        checks["resumability"] = _resumability_check(harness)
                    else:
                        checks["resumability"] = Check(
                            "resumability",
                            FAIL,
                            "resume was not attempted after an incomplete synthetic qualification",
                            {},
                        )
                except Exception as error:
                    _write_private_diagnostic(roots, report_id, "synthetic_qualification", error)
                    _set_dependent_failures(
                        checks,
                        "synthetic qualification raised an internal error; benchmark execution is blocked",
                    )

    # The user requested this exact set, even when an earlier prerequisite
    # prevents a downstream action. Every key is explicit PASS or FAIL.
    for name in _REQUIRED_CHECK_NAMES:
        if name not in checks:
            checks[name] = Check(name, FAIL, "not evaluated because a prerequisite failed", {})
    qualification_passed = all(checks[name].status == PASS for name in _REQUIRED_CHECK_NAMES)
    filename = f"colab_preflight_{report_id}.json"
    provisional = ColabPreflightReport(
        report_id=report_id,
        qualification_passed=qualification_passed,
        checks=checks,
        runtime=runtime,
        config_identity=config.public_identity(),
        qualification_summary=qualification_summary,
        public_report_filename=filename,
    )
    write_public_safe_json(roots.public_safe, filename, provisional.public_dict())
    return provisional


_REQUIRED_CHECK_NAMES = (
    "runtime_pins",
    "cuda_available",
    "device_name",
    "vram",
    "bf16_runtime_suitability",
    "disk_availability",
    "evaluator_fixtures",
    "model_retrieval",
    "model_load",
    "hidden_state_extraction",
    "repeated_generation_soak",
    "resumability",
)


def _environment_checks(
    config: ColabRuntimeConfig, roots: ArtifactRoots, report_id: str
) -> tuple[dict[str, Check], dict[str, object], Any | None]:
    """Inspect local Colab environment without model or network activity."""

    runtime: dict[str, object] = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "repository_commit": _repository_commit(_repository_root(config)),
        "package_versions": {
            name: _package_version(name)
            for name in config.runtime_lock.packages
        },
    }
    checks: dict[str, Check] = {}
    try:
        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
        runtime["torch_version"] = str(getattr(torch, "__version__", "unknown"))
        runtime["transformers_version"] = str(getattr(transformers, "__version__", "unknown"))
        runtime["torch_cuda_build"] = getattr(getattr(torch, "version", None), "cuda", None)
        checks["runtime_pins"] = _runtime_pins_check(config, runtime)
    except Exception as error:
        _write_private_diagnostic(roots, report_id, "runtime_import", error)
        checks["runtime_pins"] = Check("runtime_pins", FAIL, _safe_error(error), {})
        checks["cuda_available"] = Check("cuda_available", FAIL, _safe_error(error), {})
        checks["device_name"] = Check("device_name", FAIL, "Torch import failed", {})
        checks["vram"] = Check("vram", FAIL, "Torch import failed", {})
        checks["bf16_runtime_suitability"] = Check("bf16_runtime_suitability", FAIL, "Torch import failed", {})
        _disk_check(checks, config, roots)
        return checks, runtime, None
    try:
        cuda_available = bool(torch.cuda.is_available())
    except Exception as error:
        _write_private_diagnostic(roots, report_id, "cuda_availability", error)
        cuda_available = False
        cuda_error = _safe_error(error)
    else:
        cuda_error = "torch.cuda.is_available() returned false"
    if not cuda_available:
        checks["cuda_available"] = Check("cuda_available", FAIL, cuda_error, {})
        checks["device_name"] = Check("device_name", FAIL, "CUDA is unavailable", {})
        checks["vram"] = Check("vram", FAIL, "CUDA is unavailable", {})
        checks["bf16_runtime_suitability"] = Check("bf16_runtime_suitability", FAIL, "CUDA is unavailable", {})
        _disk_check(checks, config, roots)
        return checks, runtime, torch
    try:
        properties = torch.cuda.get_device_properties(0)
        name = str(properties.name)
        total_bytes = int(properties.total_memory)
        vram_gib = total_bytes / (1024**3)
        bf16_supported = bool(torch.cuda.is_bf16_supported())
    except Exception as error:
        _write_private_diagnostic(roots, report_id, "cuda_device_inspection", error)
        checks["cuda_available"] = Check("cuda_available", FAIL, _safe_error(error), {})
        checks["device_name"] = Check("device_name", FAIL, "CUDA device inspection failed", {})
        checks["vram"] = Check("vram", FAIL, "CUDA device inspection failed", {})
        checks["bf16_runtime_suitability"] = Check("bf16_runtime_suitability", FAIL, "CUDA device inspection failed", {})
        _disk_check(checks, config, roots)
        return checks, runtime, torch
    runtime.update(
        {
            "cuda_available": True,
            "device_name": name,
            "vram_bytes": total_bytes,
            "vram_gib": vram_gib,
            "bf16_supported": bf16_supported,
        }
    )
    checks["cuda_available"] = Check("cuda_available", PASS, "CUDA is available", {})
    checks["device_name"] = Check("device_name", PASS, name, {"device_name": name})
    checks["vram"] = Check(
        "vram",
        PASS if vram_gib >= config.qualification.minimum_vram_gib else FAIL,
        f"{vram_gib:.2f} GiB detected; minimum is {config.qualification.minimum_vram_gib} GiB",
        {"vram_bytes": total_bytes, "vram_gib": vram_gib, "minimum_vram_gib": config.qualification.minimum_vram_gib},
    )
    checks["bf16_runtime_suitability"] = Check(
        "bf16_runtime_suitability",
        PASS if bf16_supported else FAIL,
        "torch.cuda.is_bf16_supported() returned true" if bf16_supported else "GPU/runtime does not support BF16",
        {"bf16_supported": bf16_supported},
    )
    _disk_check(checks, config, roots)
    return checks, runtime, torch


def _disk_check(checks: dict[str, Check], config: ColabRuntimeConfig, roots: ArtifactRoots) -> None:
    usage = shutil.disk_usage(roots.private_root)
    free_gib = usage.free / (1024**3)
    checks["disk_availability"] = Check(
        "disk_availability",
        PASS if free_gib >= config.qualification.minimum_free_disk_gib else FAIL,
        f"{free_gib:.2f} GiB free; minimum is {config.qualification.minimum_free_disk_gib} GiB",
        {"free_bytes": usage.free, "free_gib": free_gib, "minimum_free_disk_gib": config.qualification.minimum_free_disk_gib},
    )


def _set_dependent_failures(checks: dict[str, Check], reason: str) -> None:
    for name in (
        "model_retrieval",
        "model_load",
        "hidden_state_extraction",
        "repeated_generation_soak",
        "resumability",
    ):
        checks.setdefault(name, Check(name, FAIL, reason, {}))


def _evaluator_fixture_check(
    config: ColabRuntimeConfig, roots: ArtifactRoots, report_id: str
) -> Check:
    """Run the frozen evaluator fixtures without model or benchmark access."""

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "unittest",
                "-q",
                "activation_continuation.tests.test_answer_evaluator",
            ],
            cwd=_repository_root(config),
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception as error:
        _write_private_diagnostic(roots, report_id, "evaluator_fixtures", error)
        return Check("evaluator_fixtures", FAIL, _safe_error(error), {})
    if result.returncode != 0:
        _write_private_text_diagnostic(
            roots,
            report_id,
            "evaluator_fixtures",
            "evaluator fixture subprocess failed",
            stdout=result.stdout,
            stderr=result.stderr,
        )
        return Check(
            "evaluator_fixtures",
            FAIL,
            "evaluator fixture suite failed; detailed diagnostic retained privately",
            {"return_code": result.returncode},
        )
    return Check(
        "evaluator_fixtures",
        PASS,
        "frozen deterministic evaluator fixture suite passed",
        {"return_code": result.returncode},
    )


def _runtime_pins_check(config: ColabRuntimeConfig, runtime: Mapping[str, object]) -> Check:
    actual_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    actual_packages = runtime.get("package_versions")
    package_versions = actual_packages if isinstance(actual_packages, Mapping) else {}
    mismatches: dict[str, dict[str, object]] = {}
    if actual_python != config.runtime_lock.python_major_minor:
        mismatches["python_major_minor"] = {
            "expected": config.runtime_lock.python_major_minor,
            "actual": actual_python,
        }
    actual_cuda_build = runtime.get("torch_cuda_build")
    if actual_cuda_build != config.runtime_lock.torch_cuda_build:
        mismatches["torch_cuda_build"] = {
            "expected": config.runtime_lock.torch_cuda_build,
            "actual": actual_cuda_build,
        }
    for package, expected in config.runtime_lock.packages.items():
        actual = package_versions.get(package)
        if actual != expected:
            mismatches[f"package:{package}"] = {"expected": expected, "actual": actual}
    for imported_name, runtime_key in (("torch", "torch_version"), ("transformers", "transformers_version")):
        expected = config.runtime_lock.packages[imported_name]
        actual = runtime.get(runtime_key)
        if actual != expected:
            mismatches[f"imported:{imported_name}"] = {"expected": expected, "actual": actual}
    return Check(
        "runtime_pins",
        PASS if not mismatches else FAIL,
        "all frozen runtime versions match the execution lock"
        if not mismatches
        else "one or more frozen runtime versions do not match the execution lock",
        {"mismatches": mismatches},
    )


def _qualification_execution_identity(
    config: ColabRuntimeConfig, runtime: Mapping[str, object]
) -> dict[str, object]:
    """Build a path-free identity that determines safe qualification reuse."""

    repository_commit = runtime.get("repository_commit")
    if not isinstance(repository_commit, str) or len(repository_commit) != 40:
        raise RuntimeError("checked-out repository commit is unavailable")
    package_versions = runtime.get("package_versions")
    if not isinstance(package_versions, Mapping):
        raise RuntimeError("runtime package identity is unavailable")
    return {
        "schema_version": 1,
        "config_sha256": config.fingerprint,
        "repository_commit": repository_commit,
        "python_version": runtime.get("python_version"),
        "torch_version": runtime.get("torch_version"),
        "torch_cuda_build": runtime.get("torch_cuda_build"),
        "transformers_version": runtime.get("transformers_version"),
        "package_versions": dict(package_versions),
        "device_name": runtime.get("device_name"),
        "vram_bytes": runtime.get("vram_bytes"),
        "bf16_supported": runtime.get("bf16_supported"),
    }


def _execution_identity_sha256(identity: Mapping[str, object]) -> str:
    encoded_identity = json.dumps(
        identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded_identity).hexdigest()


def _freeze_or_validate_execution_identity(
    output_directory: Path, identity: Mapping[str, object]
) -> str:
    digest = _execution_identity_sha256(identity)
    destination = output_directory / "execution_identity.json"
    payload = json.dumps(
        {
            "schema_version": 1,
            "execution_identity_sha256": digest,
            "identity": dict(identity),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8") + b"\n"
    output_directory.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != payload:
            raise RuntimeError("qualification execution identity conflicts with existing private evidence")
        return digest
    try:
        with destination.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        if destination.read_bytes() != payload:
            raise RuntimeError("qualification execution identity conflicts with existing private evidence")
    return digest


def _qualification_plan(config: ColabRuntimeConfig) -> QualificationPlan:
    return QualificationPlan(
        run_id=config.qualification.run_id,
        model_id=config.model.repo_id,
        model_revision=config.model.revision,
        tokenizer_revision=config.model.tokenizer_revision,
        cycles_per_case=config.qualification.cycles_per_case,
        generation=GenerationSpec(
            max_new_tokens=config.generation.max_new_tokens,
            do_sample=config.generation.do_sample,
            temperature=config.generation.temperature,
            top_p=config.generation.top_p,
            top_k=config.generation.top_k,
            min_p=config.generation.min_p,
        ),
        chat_template_kwargs={"enable_thinking": config.generation.thinking_mode},
        activation_layers=config.qualification.activation_layers,
        memory_growth_tolerance_bytes=config.qualification.memory_growth_tolerance_mib * 1024 * 1024,
    )


def _model_load_check(records: Sequence[Mapping[str, Any]]) -> Check:
    completed = [record for record in records if record.get("event_type") == "model_load_completed"]
    failed = [record for record in records if record.get("event_type") == "model_load_failed"]
    if completed and not failed:
        payload = completed[-1].get("payload", {})
        runner = payload.get("runner_provenance", {}) if isinstance(payload, Mapping) else {}
        return Check(
            "model_load", PASS, "native BF16 model load completed", {"runner": runner if isinstance(runner, Mapping) else {}},
        )
    return Check("model_load", FAIL, "native BF16 model load did not complete", {"failure_count": len(failed)})


def _activation_check(
    *,
    ledger_records: Sequence[Mapping[str, Any]],
    qualification_output: Path,
    diagnostic_recorder: Callable[[str, Exception], None] | None = None,
) -> Check:
    artifacts: list[Mapping[str, Any]] = []
    for record in ledger_records:
        if record.get("event_type") != "intent_completed":
            continue
        payload = record.get("payload")
        if isinstance(payload, Mapping):
            values = payload.get("activation_artifacts", [])
            if isinstance(values, list):
                artifacts.extend(value for value in values if isinstance(value, Mapping))
    if not artifacts:
        return Check("hidden_state_extraction", FAIL, "no completed activation artifacts were recorded", {})
    try:
        verified = 0
        for artifact in artifacts:
            relative = artifact.get("relative_path")
            digest = artifact.get("sha256")
            if not isinstance(relative, str) or not isinstance(digest, str):
                raise ValueError("artifact metadata is incomplete")
            parts = PurePosixPath(relative).parts
            if not parts or ".." in parts:
                raise ValueError("artifact path is unsafe")
            path = qualification_output.joinpath(*parts)
            inspection = inspect_activation_artifact(path)
            if inspection["sha256"] != digest:
                raise ValueError("artifact checksum mismatch")
            verified += 1
    except Exception as error:
        if diagnostic_recorder is not None:
            diagnostic_recorder("hidden_state_extraction", error)
        return Check("hidden_state_extraction", FAIL, _safe_error(error), {})
    return Check(
        "hidden_state_extraction",
        PASS,
        f"verified {verified} private last-prefix activation artifacts",
        {"artifact_count": verified},
    )


def _soak_check(report: Any) -> Check:
    summary = report.summary
    planned = summary.get("planned_intent_count")
    completed = summary.get("completed_intent_count")
    failures = summary.get("failed_intent_count")
    unknown = summary.get("interrupted_unknown_intent_count")
    context = summary.get("context_safety_status")
    reached_cap = summary.get("all_cycles_reached_generation_cap")
    generation_cap = summary.get("generation_cap_tokens")
    memory = summary.get("memory_stability")
    memory_status = memory.get("status") if isinstance(memory, Mapping) else None
    passed = (
        # A second invocation after a completed Drive-backed run must retain
        # its successful soak evidence rather than re-run it.  The harness
        # expresses that conservative resume state as ``no_pending_intents``.
        report.execution_status in {"synthetic_execution_finished", "no_pending_intents"}
        and isinstance(planned, int)
        and planned > 0
        and completed == planned
        and failures == 0
        and unknown == 0
        and context == "all_recorded_cycles_safe"
        and reached_cap is True
        and generation_cap == 4096
        and memory_status == "within_tolerance"
    )
    return Check(
        "repeated_generation_soak",
        PASS if passed else FAIL,
        "all fixed synthetic cycles completed with context and memory criteria"
        if passed
        else "synthetic soak did not meet every fixed completion/context/memory criterion",
        {
            "planned_intents": planned,
            "completed_intents": completed,
            "failed_intents": failures,
            "interrupted_unknown_intents": unknown,
            "context_safety_status": context,
            "all_cycles_reached_generation_cap": reached_cap,
            "generation_cap_tokens": generation_cap,
            "memory_stability_status": memory_status,
        },
    )


def _resumability_check(harness: RuntimeQualificationHarness) -> Check:
    resumed = harness.run(execute_synthetic=True)
    actions = [decision.action for decision in resumed.decisions]
    passed = resumed.execution_status == "no_pending_intents" and bool(actions) and all(
        action == "skip_completed" for action in actions
    )
    return Check(
        "resumability",
        PASS if passed else FAIL,
        "resume observed only completed intents and did not regenerate them"
        if passed
        else "resume evidence includes pending, failed, or interrupted-unknown intents",
        {"execution_status": resumed.execution_status, "resume_actions": actions},
    )


def _repository_root(config: ColabRuntimeConfig) -> Path:
    """Resolve the checkout root from the versioned configuration location."""

    try:
        return config.source_path.resolve().parents[2]
    except IndexError as error:  # pragma: no cover - guarded by repository layout
        raise RuntimeError("Colab configuration is not located beneath a repository checkout") from error


def _repository_commit(repository_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    value = result.stdout.strip()
    return value if value else None


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _safe_error(error: Exception) -> str:
    """Return a public-safe error category, never arbitrary exception text."""

    return f"{type(error).__name__}; detailed diagnostic retained privately"


def _write_private_diagnostic(
    roots: ArtifactRoots, report_id: str, phase: str, error: Exception
) -> None:
    _write_private_text_diagnostic(
        roots,
        report_id,
        phase,
        f"{type(error).__name__}: {error}",
        stdout=None,
        stderr=None,
    )


def _write_private_text_diagnostic(
    roots: ArtifactRoots,
    report_id: str,
    phase: str,
    message: str,
    *,
    stdout: str | None,
    stderr: str | None,
) -> None:
    """Persist detailed diagnostics privately without affecting public output."""

    if not phase.replace("_", "").isalnum():
        raise ValueError("diagnostic phase must be a safe identifier")
    destination = roots.provenance / f"preflight_diagnostic_{report_id}_{phase}.json"
    payload = json.dumps(
        {
            "schema_version": 1,
            "report_id": report_id,
            "phase": phase,
            "message": message[:16000],
            "stdout": stdout[:16000] if stdout is not None else None,
            "stderr": stderr[:16000] if stderr is not None else None,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8") + b"\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except (FileExistsError, OSError):
        # A report ID is unique, so an existing file is the immutable first
        # diagnostic rather than an invitation to overwrite it.
        return


def _report_id(config: ColabRuntimeConfig) -> str:
    # Public-safe reports are written exclusively.  Microseconds avoid a
    # collision if a user deliberately reruns the preflight within one second.
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{config.qualification.run_id}-{config.fingerprint[:12]}-{timestamp}"


def _print_report(report: ColabPreflightReport) -> None:
    print("COLAB PREFLIGHT REPORT")
    for name in _REQUIRED_CHECK_NAMES:
        check = report.checks[name]
        print(f"{name}: {check.status} — {check.detail}")
    retrieval = report.checks.get("model_retrieval")
    if retrieval is not None:
        print(f"model_retrieval: {retrieval.status} — {retrieval.detail}")
    print(f"qualification_passed: {'PASS' if report.qualification_passed else 'FAIL'}")
    print(f"public_safe_report_filename: {report.public_report_filename}")
    print("Return the public-safe JSON report and this PASS/FAIL table to Codex before benchmark work.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the activation-continuation Colab preflight")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--private-artifact-root", type=Path, required=True)
    parser.add_argument(
        "--execute-synthetic",
        action="store_true",
        help="Explicitly allow the non-benchmark synthetic qualification; default is dry-run only.",
    )
    args = parser.parse_args(argv)
    config = load_colab_runtime_config(args.config)
    report = run_colab_preflight(
        config=config,
        private_artifact_root=args.private_artifact_root,
        execute_synthetic=args.execute_synthetic,
    )
    _print_report(report)
    return 0 if report.qualification_passed else 2


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
