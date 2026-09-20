"""Hard gate that future benchmark code must pass before it can execute.

There is deliberately no benchmark generator in this portability package. The
scientific protocol requires a tier decision and frozen manifest after a
successful Colab qualification; this module makes an accidental invocation
before those actions fail loudly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .config import ColabRuntimeConfig


class BenchmarkGateError(RuntimeError):
    """A benchmark run was requested before its required frozen prerequisites."""


def verify_benchmark_gate(
    *,
    config: ColabRuntimeConfig,
    public_preflight_report: Mapping[str, Any],
    repository_root: Path,
) -> None:
    """Validate prerequisites without importing a dataset or model.

    A future benchmark-study runner must call this before creating any model
    request. It intentionally does not infer a tier, generate a manifest, or
    perform a model call on its own.
    """

    if public_preflight_report.get("qualification_passed") is not True:
        raise BenchmarkGateError("benchmark generation is blocked: Colab qualification did not pass")
    report_config = public_preflight_report.get("config")
    if not isinstance(report_config, Mapping):
        raise BenchmarkGateError("benchmark generation is blocked: public preflight report is malformed")
    if report_config.get("config_sha256") != config.fingerprint:
        raise BenchmarkGateError("benchmark generation is blocked: preflight configuration mismatch")
    manifest = repository_root / config.benchmark_gate.manifest_path
    if not manifest.is_file():
        raise BenchmarkGateError(
            "benchmark generation is blocked: the required frozen study manifest does not exist"
        )
    try:
        content = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BenchmarkGateError("benchmark generation is blocked: study manifest is unreadable") from error
    if not isinstance(content, Mapping):
        raise BenchmarkGateError("benchmark generation is blocked: study manifest is not an object")
    declared_hash = content.get("manifest_sha256")
    if not isinstance(declared_hash, str) or len(declared_hash) != 64:
        raise BenchmarkGateError(
            "benchmark generation is blocked: study manifest lacks a declared immutable hash"
        )
    unhashed = dict(content)
    unhashed.pop("manifest_sha256", None)
    actual_hash = hashlib.sha256(
        json.dumps(unhashed, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    if actual_hash != declared_hash:
        raise BenchmarkGateError(
            "benchmark generation is blocked: study manifest hash does not match its canonical content"
        )
    _verify_manifest_execution_binding(config, public_preflight_report, content)
    _verify_tier_decision(public_preflight_report, content)


def _verify_manifest_execution_binding(
    config: ColabRuntimeConfig,
    public_preflight_report: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    binding = manifest.get("execution_binding")
    report_runtime = public_preflight_report.get("runtime")
    if not isinstance(binding, Mapping) or not isinstance(report_runtime, Mapping):
        raise BenchmarkGateError(
            "benchmark generation is blocked: manifest lacks an execution binding to the accepted preflight"
        )
    expected = {
        "config_sha256": config.fingerprint,
        "preflight_report_id": public_preflight_report.get("report_id"),
        "repository_commit": report_runtime.get("repository_commit"),
        "model_revision": config.model.revision,
        "tokenizer_revision": config.model.tokenizer_revision,
    }
    for field, value in expected.items():
        if not isinstance(value, str) or binding.get(field) != value:
            raise BenchmarkGateError(
                f"benchmark generation is blocked: manifest execution binding mismatches {field}"
            )


def _verify_tier_decision(
    public_preflight_report: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    decision = manifest.get("tier_decision")
    if not isinstance(decision, Mapping):
        raise BenchmarkGateError(
            "benchmark generation is blocked: manifest lacks an explicit post-qualification tier decision"
        )
    if decision.get("tier") not in {"A", "B", "C"}:
        raise BenchmarkGateError("benchmark generation is blocked: tier decision is not A, B, or C")
    if decision.get("qualification_report_id") != public_preflight_report.get("report_id"):
        raise BenchmarkGateError(
            "benchmark generation is blocked: tier decision is not bound to this qualification report"
        )
    estimate = decision.get("full_study_cost_estimate")
    if not isinstance(estimate, Mapping):
        raise BenchmarkGateError(
            "benchmark generation is blocked: tier decision lacks the required full-study cost estimate"
        )
    required = (
        "projected_total_runtime_seconds",
        "projected_total_private_disk_bytes",
        "projected_peak_vram_bytes",
    )
    if any(type(estimate.get(field)) not in {int, float} or estimate[field] <= 0 for field in required):
        raise BenchmarkGateError(
            "benchmark generation is blocked: full-study cost estimate is incomplete or non-positive"
        )


def explain_no_benchmark_execution() -> str:
    """User-facing statement used by the default-disabled notebook cell."""

    return (
        "STOP: no benchmark runner is included or invoked by this Colab portability package. "
        "Return the public-safe preflight report for review; preserve the frozen protocol and "
        "create no benchmark artifact until the qualification gate is accepted."
    )
